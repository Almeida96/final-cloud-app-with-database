"""Course catalog, authentication and the final assessment flow."""
import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.views.decorators.http import require_GET, require_POST
from .models import Course, Enrollment, Question, Choice, Submission

logger = logging.getLogger(__name__)
User = get_user_model()


def registration_request(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('psw', '')
        if not username or not password:
            messages.error(request, 'Please provide a username and password.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
            user = User.objects.create_user(
                username=username, password=password,
                first_name=request.POST.get('firstname', '').strip(),
                last_name=request.POST.get('lastname', '').strip(),
            )
            login(request, user)
            return redirect('onlinecourse:index')
    return render(request, 'onlinecourse/user_registration_bootstrap.html')


def login_request(request):
    if request.method == 'POST':
        user = authenticate(
            request, username=request.POST.get('username', ''),
            password=request.POST.get('psw', ''),
        )
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'onlinecourse/user_login_bootstrap.html')


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    return user.is_authenticated and Enrollment.objects.filter(user=user, course=course).exists()


class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        courses = list(Course.objects.order_by('-total_enrollment', 'name')[:20])
        for course in courses:
            course.is_enrolled = check_if_enrolled(self.request.user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_details_bootstrap.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lessons'] = self.object.lesson_set.all().order_by('order', 'id')
        context['questions'] = (Question.objects.filter(lesson__course=self.object)
                                .select_related('lesson')
                                .prefetch_related('choice_set')
                                .order_by('lesson__order', 'id'))
        context['is_enrolled'] = check_if_enrolled(self.request.user, self.object)
        return context


@login_required
@require_POST
def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    _, created = Enrollment.objects.get_or_create(
        user=request.user, course=course, defaults={'mode': Enrollment.HONOR}
    )
    if created:
        course.total_enrollment = Enrollment.objects.filter(course=course).count()
        course.save(update_fields=['total_enrollment'])
    return redirect('onlinecourse:course_details', pk=course.pk)


@login_required
@require_POST
def submit(request, course_id):
    """Save selected answers only for an enrolled user and this course."""
    course = get_object_or_404(Course, pk=course_id)
    enrollment = Enrollment.objects.filter(course=course, user=request.user).first()
    if enrollment is None:
        return HttpResponseForbidden('Enroll in the course before taking the exam.')

    raw_ids = request.POST.getlist('choice')
    if len(raw_ids) > 1000 or not all(
        raw_id.isascii() and raw_id.isdecimal() and len(raw_id) <= 18
        for raw_id in raw_ids
    ):
        return HttpResponseForbidden('Invalid choice identifier.')
    choice_ids = {int(value) for value in raw_ids}
    selected = list(Choice.objects.filter(
        id__in=choice_ids, question__lesson__course=course
    ))
    if len(selected) != len(choice_ids):
        return HttpResponseForbidden('Some selected choices are outside this exam.')

    with transaction.atomic():
        submission = Submission.objects.create(
            enrollment=enrollment, grading_snapshot=grade_exam(course, choice_ids)
        )
        submission.choices.set(selected)
    return redirect('onlinecourse:show_exam_result',
                    course_id=course.id, submission_id=submission.id)


@login_required
@require_GET
def show_exam_result(request, course_id, submission_id):
    """Display the saved assessment, or grade legacy attempts without snapshots."""
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(
        Submission, pk=submission_id,
        enrollment__user=request.user, enrollment__course=course,
    )
    snapshot = submission.grading_snapshot
    if snapshot is None:
        snapshot = grade_exam(course, set(submission.choices.values_list('id', flat=True)))
    return render(request, 'onlinecourse/exam_result_bootstrap.html', {
        'course': course, 'submission': submission,
        **snapshot, 'legacy_grading': submission.grading_snapshot is None,
    })


def grade_exam(course, chosen_ids):
    """Capture the assessment wording and scores at submission time."""
    questions = (Question.objects.filter(lesson__course=course)
                 .select_related('lesson')
                 .prefetch_related('choice_set')
                 .order_by('lesson__order', 'id'))
    results = []
    earned = 0
    possible = 0
    for question in questions:
        choices = list(question.choice_set.all())
        selected = [choice for choice in choices if choice.id in chosen_ids]
        correct = [choice for choice in choices if choice.is_correct]
        is_correct = bool(correct) and {c.id for c in selected} == {c.id for c in correct}
        possible += question.grade
        if is_correct:
            earned += question.grade
        results.append({
            'question': {'question_text': question.question_text},
            'selected': [{'choice_text': choice.choice_text} for choice in selected],
            'correct_choices': [{'choice_text': choice.choice_text} for choice in correct], 'correct': is_correct,
        })
    percentage = round(100 * earned / possible, 1) if possible else 0
    return {'results': results, 'earned_score': earned, 'total_score': possible,
            'percentage': percentage, 'passed': possible > 0 and percentage >= 70}

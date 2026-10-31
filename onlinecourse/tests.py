"""Integration tests of exam submission, grading and access control."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Choice, Course, Enrollment, Lesson, Question, Submission


class ExamFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.student = User.objects.create_user(username='test-student', password='strongpass1234')
        cls.other = User.objects.create_user(username='test-other', password='strongpass1234')
        cls.course = Course.objects.create(name='Test Course', description='Sample course')
        cls.lesson = Lesson.objects.create(course=cls.course, title='Basics', content='Lesson content')
        cls.question = Question.objects.create(
            lesson=cls.lesson, question_text='Select both correct options', grade=4
        )
        cls.correct_a = Choice.objects.create(question=cls.question, choice_text='A', is_correct=True)
        cls.correct_b = Choice.objects.create(question=cls.question, choice_text='B', is_correct=True)
        cls.incorrect = Choice.objects.create(question=cls.question, choice_text='C', is_correct=False)
        cls.enrollment = Enrollment.objects.create(user=cls.student, course=cls.course)

    def test_course_details_shows_lessons_and_exam(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('onlinecourse:course_details', args=(self.course.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Basics')
        self.assertContains(response, 'Select both correct options')
        self.assertContains(response, 'Submit exam')

    def test_correct_multiselect_is_full_score(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse('onlinecourse:submit', args=(self.course.id,)), {
            'choice': [str(self.correct_a.id), str(self.correct_b.id)]
        }, follow=True)
        self.assertContains(response, 'Congratulations!')
        self.assertContains(response, '100.0%')
        self.assertEqual(Submission.objects.count(), 1)

    def test_partial_answer_scores_zero(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse('onlinecourse:submit', args=(self.course.id,)), {
            'choice': [str(self.correct_a.id)]
        }, follow=True)
        self.assertContains(response, 'Keep learning!')
        self.assertContains(response, '0.0%')

    def test_other_student_cannot_view_attempt(self):
        submission = Submission.objects.create(enrollment=self.enrollment)
        self.client.force_login(self.other)
        response = self.client.get(reverse('onlinecourse:show_exam_result',
                                           args=(self.course.id, submission.id)))
        self.assertEqual(response.status_code, 404)

    def test_unenrolled_student_cannot_submit(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('onlinecourse:submit', args=(self.course.id,)), {
            'choice': [str(self.correct_a.id)]
        })
        self.assertEqual(response.status_code, 403)

    def test_other_course_choices_rejected(self):
        other_course = Course.objects.create(name='Other', description='Other')
        lesson = Lesson.objects.create(course=other_course, title='Other', content='Other')
        question = Question.objects.create(lesson=lesson, question_text='External')
        choice = Choice.objects.create(question=question, choice_text='External', is_correct=True)
        self.client.force_login(self.student)
        response = self.client.post(reverse('onlinecourse:submit', args=(self.course.id,)), {
            'choice': [str(choice.id)]
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Submission.objects.count(), 0)

    def test_get_cannot_submit_exam(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('onlinecourse:submit', args=(self.course.id,)))
        self.assertEqual(response.status_code, 405)

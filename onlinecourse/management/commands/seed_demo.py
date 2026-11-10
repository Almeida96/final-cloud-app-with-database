"""Local demo data for real screenshots and testing (never use on production)."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from onlinecourse.models import Instructor, Learner, Course, Lesson, Enrollment, Question, Choice


class Command(BaseCommand):
    help = 'Seed a sample course and temporary local admin/student accounts.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data is available only with DEBUG enabled.")
        User = get_user_model()
        admin, created = User.objects.get_or_create(username='demo_admin')
        if created:
            admin.is_staff = True
            admin.is_superuser = True
            admin.set_password('admin12345')
            admin.save()

        student, created = User.objects.get_or_create(username='demo_student')
        if created:
            student.first_name = 'Demo'
            student.set_password('student12345')
            student.save()

        instructor, _ = Instructor.objects.get_or_create(
            user=admin, defaults={'total_learners': 1}
        )
        Learner.objects.get_or_create(user=student)
        course, _ = Course.objects.update_or_create(
            name='Django & SQL Fundamentals',
            defaults={
                'description': 'Learn Django, relational databases and the ORM.',
                'image': 'course_images/django.png',
            },
        )
        course.instructors.add(instructor)
        Enrollment.objects.get_or_create(user=student, course=course)
        course.total_enrollment = Enrollment.objects.filter(course=course).count()
        course.save(update_fields=['total_enrollment'])

        units = [
            ('Django Basics', 'Learn models, views, templates and URL routing.'),
            ('Relational Databases', 'Learn SQL tables, queries and relationships.'),
            ('Working with the ORM', 'Connect Python code to SQL databases.'),
        ]
        lessons = []
        for order, (title, content) in enumerate(units):
            lesson, _ = Lesson.objects.update_or_create(
                course=course, order=order,
                defaults={'title': title, 'content': content},
            )
            lessons.append(lesson)

        questions = [
            (lessons[0], 'Which Django component defines database structure?', 2,
             [('Models', True), ('Templates', False), ('URLs', False)]),
            (lessons[1], 'Which SQL statement retrieves rows from a table?', 2,
             [('SELECT', True), ('DELETE', False), ('INSERT', False)]),
            (lessons[2], 'Which capabilities does Django ORM support?', 3,
             [('Creating database records', True), ('Filtering database records', True),
              ('Styling a page using CSS', False)]),
            (lessons[0], 'Where do you define incoming Django URL routes?', 3,
             [('urls.py', True), ('models.py', False), ('settings.py', False)]),
        ]
        for lesson, text, grade, answer_list in questions:
            question, _ = Question.objects.update_or_create(
                lesson=lesson, question_text=text, defaults={'grade': grade},
            )
            for choice_text, is_correct in answer_list:
                Choice.objects.update_or_create(
                    question=question, choice_text=choice_text,
                    defaults={'is_correct': is_correct},
                )
        self.stdout.write(self.style.SUCCESS(
            'Demo data ready. Existing account passwords and privileges were preserved. See README for credentials of newly created demo accounts.'
        ))

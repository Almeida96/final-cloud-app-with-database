# Online Course Assessments

A Django course catalog with enrollment, multi-select exams and saved results. Based on the [IBM online-course project](https://github.com/ibm-developer-skills-network/final-cloud-app-with-database).

## Run locally

Requires Python 3.11 or later. Create and activate a virtual environment, then run:

```sh
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000
```

Open `http://127.0.0.1:8000/onlinecourse/`. On a fresh database the demo command creates `demo_student` with password `student12345` and `demo_admin` with password `admin12345`. These are local exercise accounts. Existing accounts keep their passwords and privileges when the command is repeated; seeding is rejected with `DJANGO_DEBUG=0`.

The sample course contains three lessons and four questions. Sign in as the student, read a lesson, select your answers and submit the exam. The admin interface at `/admin/` lets you edit course content, questions and choices.

## Assessment behavior

- A student must be enrolled before submitting answers.
- Choices must belong to the selected course; identifiers from another exam are rejected.
- Multi-select questions earn their points only when the selected set exactly matches the correct set. Unanswered questions receive zero points.
- The pass mark is 70%. A course without graded questions does not count as a pass.
- New submissions store the question wording, selected answers, correct answers and score at submission time. Editing questions later does not rewrite a student's result.
- Earlier submissions without a grading snapshot are labeled on their result page and use the current question data; historical wording cannot be reconstructed.
- Students can view only their own attempts. SQLite retains enrollment and submissions across restarts.

This is an educational application, not an accredited assessment platform. It has no proctoring, payment integration, email verification or public deployment configuration. Deleting a course or enrollment removes dependent attempts. The demo command may update its sample lesson content; use a disposable database for demonstrations.

## Validate changes

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Tests exercise multi-select grading, enrollment and ownership boundaries, tampered identifiers, saved-result stability and non-destructive demo account seeding. CI also creates browser screenshots from a real seeded session.

[Course submission guide](SUBMISSION_GUIDE.md) | [Apache 2.0 license](LICENSE)

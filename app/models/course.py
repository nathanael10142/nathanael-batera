# Lightweight placeholder for Course-related models in Firestore deployment.
# Original SQLAlchemy implementation archived in backend/legacy_sql_backup.
from types import SimpleNamespace

class Course(SimpleNamespace):
    pass

class CourseAssignment(SimpleNamespace):
    pass

class CourseEnrollment(SimpleNamespace):
    pass

class Grade(SimpleNamespace):
    pass

class Teacher(SimpleNamespace):
    pass

__all__ = ["Course","CourseAssignment","CourseEnrollment","Grade","Teacher"]
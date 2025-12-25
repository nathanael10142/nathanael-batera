"""
Modèles : Étudiants et leur parcours académique
"""
# Lightweight placeholder for student models in Firestore deployment.
from types import SimpleNamespace

class Student(SimpleNamespace):
    pass

class AcademicRecord(SimpleNamespace):
    pass

class Promotion(SimpleNamespace):
    pass

class Class(SimpleNamespace):
    pass

class CycleType(SimpleNamespace):
    pass

class YearLevel(SimpleNamespace):
    pass

class StudentStatus(SimpleNamespace):
    pass

__all__ = ["Student","AcademicRecord","Promotion","Class","CycleType","YearLevel","StudentStatus"]
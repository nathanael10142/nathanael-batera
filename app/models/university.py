"""
Modèles : Structure universitaire (Université → Faculté → Département → Option)
"""

# Lightweight placeholder for university models in Firestore deployment.
from types import SimpleNamespace

class University(SimpleNamespace):
    pass

class Faculty(SimpleNamespace):
    pass

class Department(SimpleNamespace):
    pass

class Option(SimpleNamespace):
    pass

class AcademicYear(SimpleNamespace):
    pass

class Session(SimpleNamespace):
    pass

__all__ = ["University","Faculty","Department","Option","AcademicYear","Session"]
"""
Re-exports légers pour intégration Firestore.
Ce fichier expose des noms utilisés ailleurs mais évite d'exécuter
logique SQL lourde au démarrage.
"""

from importlib import import_module

# Try to prefer Firestore models when firebase_admin is available
try:
    _fm = import_module("app.models.firestore_models")
    User = getattr(_fm, "User")
    Role = getattr(_fm, "Role", type("Role", (), {}))
    Permission = getattr(_fm, "Permission", type("Permission", (), {}))
    Course = getattr(_fm, "UE")
    Grade = getattr(_fm, "Grade")
    Student = getattr(_fm, "Student")
except Exception:
    # Fallback to SimpleNamespace placeholders
    from types import SimpleNamespace

    User = SimpleNamespace
    Role = SimpleNamespace
    Permission = SimpleNamespace
    Course = SimpleNamespace
    Grade = SimpleNamespace
    Student = SimpleNamespace

__all__ = ["User", "Role", "Permission", "Course", "Grade", "Student"]
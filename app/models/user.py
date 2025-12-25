"""
Modèles : Utilisateurs, rôles et permissions
"""
# Lightweight placeholders for User/Role/Permission used in Firestore deployment.
# Original SQLAlchemy model moved to backend/legacy_sql_backup.
from types import SimpleNamespace

# Minimal classes used by the application at runtime.
# They are simple holders and should not be used for ORM operations.
class User(SimpleNamespace):
    pass

class Role(SimpleNamespace):
    pass

class Permission(SimpleNamespace):
    pass

role_permissions = None

__all__ = ["User", "Role", "Permission", "role_permissions"]
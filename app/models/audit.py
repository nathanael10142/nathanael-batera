"""
Modèles : Audit et traçabilité
"""

# Lightweight placeholder for audit models in Firestore deployment.
from types import SimpleNamespace

class AuditLog(SimpleNamespace):
    pass

class SystemLog(SimpleNamespace):
    pass

__all__ = ["AuditLog","SystemLog"]
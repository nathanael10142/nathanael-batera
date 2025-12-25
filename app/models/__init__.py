"""
Re-exports légers pour intégration Firestore.
Ce fichier expose des noms utilisés ailleurs mais évite d'exécuter
logique SQL lourde au démarrage.
"""

from types import SimpleNamespace

# Provide minimal placeholders to avoid import errors when code expects these names
User = SimpleNamespace
Role = SimpleNamespace
Permission = SimpleNamespace
Course = SimpleNamespace
Grade = SimpleNamespace
Student = SimpleNamespace

__all__ = ["User","Role","Permission","Course","Grade","Student"]
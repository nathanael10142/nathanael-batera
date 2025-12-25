"""
Compatibility shim `models` for legacy imports (e.g. `from models import Utilisateur`).
This file re-exports classes from `app.models` using the most likely French names
used across the older code in this repository.

It aims to make the application importable for deployment while you complete the
migration to the English `app.models` package names. It does NOT change any
real model definitions.
"""

from typing import Any

try:
    # Import the canonical models package
    import app.models as _am
except Exception:
    _am = None


def _alias(name: str, fallback_name: str) -> Any:
    """Return the object from app.models with fallback to a placeholder.
    """
    if _am is None:
        class _Missing:
            def __init__(self, *a, **k):
                raise RuntimeError(f"Model '{name}' is unavailable because 'app.models' could not be imported.")
        return _Missing
    return getattr(_am, fallback_name, None) or getattr(_am, name, None) or None


# Common aliases (French -> English)
Utilisateur = _alias("Utilisateur", "User")
Etudiant = _alias("Etudiant", "Student")
Universite = _alias("Universite", "University")
Faculte = _alias("Faculte", "Faculty")
Departement = _alias("Departement", "Department")
OptionFiliere = _alias("OptionFiliere", "Option")
Option = _alias("Option", "Option")
Promotion = _alias("Promotion", "Promotion")
Groupe = _alias("Groupe", "Group")
UE = _alias("UE", "Course")
EtudiantUE = _alias("EtudiantUE", "Grade")
Paiement = _alias("Paiement", "Payment")
Document = _alias("Document", "Document")
Role = _alias("Role", "Role")

# Re-export english names as well if present
try:
    User = getattr(_am, "User")
except Exception:
    User = None

# Base
try:
    Base = getattr(_am, "Base")
except Exception:
    Base = None

# Expose everything we can from app.models for convenience
if _am is not None:
    for _name in dir(_am):
        if not _name.startswith("_"):
            globals().setdefault(_name, getattr(_am, _name))

__all__ = [k for k in globals().keys() if not k.startswith("_")]

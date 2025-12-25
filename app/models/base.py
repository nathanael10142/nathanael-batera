"""
Archived SQLAlchemy base model.
The original implementation has been moved to:
  backend/legacy_sql_backup/app/models/base.py

This placeholder prevents runtime imports of SQLAlchemy in a Firestore-only deployment.
"""

# Placeholder export used by code that imports app.models.base
Base = None

class BaseModel:
    """Lightweight placeholder for the original BaseModel.
    Do not rely on this for SQL operations. See legacy_sql_backup for original code.
    """
    pass
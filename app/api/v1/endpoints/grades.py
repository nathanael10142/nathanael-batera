from typing import Any, List
from fastapi import APIRouter, Depends
from firebase_admin import firestore

from app.core.security import get_current_active_user
from app.models.user import User
from app.models.firestore_models import list_docs

router = APIRouter()

@router.get("/me")
async def read_my_grades(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Retrieve current user grades from Firestore using helper"""
    if not current_user:
        return []

    user_id = str(getattr(current_user, "id", current_user))
    docs = list_docs("grades", where=[("student_uid","==",user_id)], limit=100)
    return docs
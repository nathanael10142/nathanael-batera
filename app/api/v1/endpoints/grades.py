from typing import Any, List
from fastapi import APIRouter, Depends
from firebase_admin import firestore

from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/me")
async def read_my_grades(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Retrieve current user grades from Firestore"""
    if not current_user:
        return []

    db = firestore.client()
    grades_ref = db.collection("grades").where("student_uid", "==", str(current_user.id)).limit(100)
    docs = grades_ref.stream()
    return [d.to_dict() for d in docs]
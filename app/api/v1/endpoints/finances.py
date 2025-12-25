from typing import Any, List
from fastapi import APIRouter, Depends
from firebase_admin import firestore

from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/me")
async def read_my_payments(current_user: User = Depends(get_current_active_user)) -> Any:
    """Retrieve current user payments from Firestore"""
    if not current_user:
        return []

    db = firestore.client()
    payments_ref = db.collection("payments").where("student_uid", "==", str(current_user.id)).limit(100)
    docs = payments_ref.stream()
    return [d.to_dict() for d in docs]
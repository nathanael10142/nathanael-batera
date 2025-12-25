from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import firestore

from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/me")
async def read_student_profile(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get current student profile from Firestore"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    db = firestore.client()
    doc = db.collection("users").document(str(current_user.id)).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User profile not found")

    profile = doc.to_dict() or {}
    # Support multiple possible field names used across the project
    if "etudiant" in profile:
        return profile["etudiant"]
    if "student" in profile:
        return profile["student"]
    # Fallback: return the whole profile document
    return profile
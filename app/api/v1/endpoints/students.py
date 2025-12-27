from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_active_user
from app.models.firestore_models import get_doc
from app.models.user import User

router = APIRouter()

@router.get("/me")
async def read_student_profile(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get current student profile from Firestore (uses helper)
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Support current_user being either an object with an `id` attribute or a raw id
    user_id = str(getattr(current_user, "id", current_user))
    profile = get_doc("users", user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    # Support multiple possible field names used across the project
    if "etudiant" in profile:
        return profile["etudiant"]
    if "student" in profile:
        return profile["student"]
    # Fallback: return the whole profile document
    return profile
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_current_active_user
from database import get_session
from models import Utilisateur, Etudiant

router = APIRouter()

@router.get("/me")
async def read_student_profile(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session)
) -> Any:
    """Get current student profile"""
    if not current_user.etudiant:
        return {"error": "User is not a student"}
    return current_user.etudiant
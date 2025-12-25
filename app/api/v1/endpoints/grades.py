from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_current_active_user
from database import get_session
from models import EtudiantUE, Utilisateur

router = APIRouter()

@router.get("/me")
async def read_my_grades(
    db: AsyncSession = Depends(get_session),
    current_user: Utilisateur = Depends(get_current_active_user)
) -> Any:
    """Retrieve current user grades"""
    if not current_user.etudiant:
        return []
    
    result = await db.execute(select(EtudiantUE).where(EtudiantUE.etudiant_id == current_user.etudiant.id))
    return result.scalars().all()
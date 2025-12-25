from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_current_active_user
from database import get_session
from models import Paiement, Utilisateur

router = APIRouter()

@router.get("/me")
async def read_my_payments(
    db: AsyncSession = Depends(get_session),
    current_user: Utilisateur = Depends(get_current_active_user)
) -> Any:
    """Retrieve current user payments"""
    if not current_user.etudiant:
        return []
    
    result = await db.execute(select(Paiement).where(Paiement.etudiant_id == current_user.etudiant.id))
    return result.scalars().all()
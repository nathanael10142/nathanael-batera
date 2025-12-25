from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_session
from models import Faculte

router = APIRouter()

@router.get("/")
async def read_faculties(db: AsyncSession = Depends(get_session)) -> Any:
    """Retrieve all faculties (public)"""
    result = await db.execute(select(Faculte))
    return result.scalars().all()
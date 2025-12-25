from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_session
from models import UE

router = APIRouter()

@router.get("/")
async def read_courses(db: AsyncSession = Depends(get_session)) -> Any:
    """Retrieve courses"""
    result = await db.execute(select(UE).limit(100))
    return result.scalars().all()
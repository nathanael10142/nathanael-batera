from typing import Any
from fastapi import APIRouter
from app.models.firestore_models import list_docs, public_list

router = APIRouter()

@router.get("/")
async def read_courses(limit: int = 200) -> Any:
    """Retrieve courses from Firestore using helper"""
    return public_list('courses', limit=limit)
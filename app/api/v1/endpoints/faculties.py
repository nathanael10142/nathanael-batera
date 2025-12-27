from typing import Any
from fastapi import APIRouter
from app.models.firestore_models import public_list

router = APIRouter()

@router.get("/")
async def read_faculties(limit: int = 100) -> Any:
    """Retrieve visible faculties using the centralized public_list helper."""
    # public_list will fetch documents and exclude those where is_deleted == True
    return public_list("faculties", limit=limit)
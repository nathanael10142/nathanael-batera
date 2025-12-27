from typing import Any, List
from fastapi import APIRouter
from app.models.firestore_models import list_docs

router = APIRouter()

@router.get("/")
async def read_faculties(limit: int = 100) -> Any:
    """Retrieve all faculties from Firestore using helper"""
    docs = list_docs("faculties", where=[("is_deleted","==",False)], limit=limit)
    return docs
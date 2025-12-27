from typing import Any, List
from fastapi import APIRouter
from app.models.firestore_models import list_docs

router = APIRouter()

@router.get("/")
async def read_faculties(limit: int = 100) -> Any:
    """Retrieve all faculties from Firestore using helper"""
    docs = list_docs("faculties", limit=limit)
    try:
        visible = [d for d in docs if not d.get('is_deleted', False)]
    except Exception:
        visible = docs
    return visible
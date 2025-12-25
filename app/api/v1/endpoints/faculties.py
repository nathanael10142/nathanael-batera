from typing import Any, List
from fastapi import APIRouter
from firebase_admin import firestore

router = APIRouter()

@router.get("/")
async def read_faculties() -> Any:
    """Retrieve all faculties from Firestore"""
    db = firestore.client()
    docs = db.collection("faculties").limit(100).stream()
    return [d.to_dict() for d in docs]
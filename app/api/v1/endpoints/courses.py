from typing import Any, List
from fastapi import APIRouter
from firebase_admin import firestore

router = APIRouter()

@router.get("/")
async def read_courses() -> Any:
    """Retrieve courses from Firestore"""
    db = firestore.client()
    docs = db.collection("courses").limit(200).stream()
    return [d.to_dict() for d in docs]
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from google.cloud.firestore import Client as FirestoreClient

from app.core.firebase_connector import get_firestore_client
from app.schemas.user import User, UserCreate, UserUpdate
from app.crud import crud_user_firebase

router = APIRouter()

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(
    *,
    db: FirestoreClient = Depends(get_firestore_client),
    user_in: UserCreate
):
    """Crée un nouvel utilisateur."""
    # On pourrait ajouter une vérification pour voir si l'email existe déjà
    user = crud_user_firebase.create_user(db=db, user_in=user_in)
    return user

@router.get("/", response_model=List[User])
def read_users(
    db: FirestoreClient = Depends(get_firestore_client)
):
    """Récupère la liste de tous les utilisateurs."""
    return crud_user_firebase.get_all_users(db=db)

@router.get("/{user_id}", response_model=User)
def read_user_by_id(
    user_id: str,
    db: FirestoreClient = Depends(get_firestore_client)
):
    """Récupère un utilisateur par son ID."""
    user = crud_user_firebase.get_user(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: FirestoreClient = Depends(get_firestore_client)
):
    """Met à jour un utilisateur."""
    return crud_user_firebase.update_user(db=db, user_id=user_id, user_in=user_in)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, db: FirestoreClient = Depends(get_firestore_client)):
    """Supprime un utilisateur."""
    crud_user_firebase.delete_user(db=db, user_id=user_id)
    return {"ok": True} # Le status code 204 ne renvoie pas de corps
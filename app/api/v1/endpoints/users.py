"""
Routes pour la gestion des utilisateurs (création, etc.)
"""
from typing import List
from fastapi import APIRouter, HTTPException, Body, Depends
from firebase_admin import auth, firestore
from pydantic import BaseModel, EmailStr

# Imports pour la sécurité et les modèles
from app.core.security import get_current_active_user, require_permission, Permissions
from app.schemas.user import User as UserSchema

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str = "student" # Rôle par défaut

@router.post("/", status_code=201, summary="Create a new user")
async def create_user(user_in: UserCreate):
    """
    Créer un nouvel utilisateur dans Firebase Auth et un profil dans Firestore.I
    """
    try:
        # 1. Créer l'utilisateur dans Firebase Authentication
        user_record = auth.create_user(
            email=user_in.email,
            password=user_in.password,
            display_name=user_in.full_name
        )

        # 2. Créer un document de profil utilisateur dans Firestore
        db = firestore.client()
        user_profile_data = {
            "uid": user_record.uid,
            "email": user_in.email,
            "full_name": user_in.full_name,
            "role": user_in.role,
            "created_at": firestore.SERVER_TIMESTAMP
        }
        db.collection("users").document(user_record.uid).set(user_profile_data)

        return {
            "message": "Utilisateur créé avec succès",
            "uid": user_record.uid,
            "email": user_record.email
        }

    except auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=400,
            detail=f"L'email '{user_in.email}' est déjà utilisé par un autre compte."
        )
    except Exception as e:
        # Pour les autres erreurs potentielles de Firebase
        raise HTTPException(
            status_code=500,
            detail=f"Une erreur est survenue lors de la création de l'utilisateur: {e}"
        )

@router.get("/", response_model=List[UserSchema], summary="List all users (Admin only)")
async def read_users(
    current_user: UserSchema = Depends(require_permission(Permissions.ADMIN_MANAGE_USERS)),
    limit: int = 100
):
    """
    Récupère une liste de tous les utilisateurs depuis Firestore.
    Cette route est protégée et accessible uniquement par les administrateurs.
    """
    try:
        db = firestore.client()
        users_ref = db.collection("users").limit(limit).stream()
        
        users_list = []
        for doc in users_ref:
            user_data = doc.to_dict()
            users_list.append(UserSchema(**user_data))
            
        return users_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching users: {e}")

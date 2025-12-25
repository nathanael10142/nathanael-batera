"""
Routes pour la gestion des utilisateurs (création, etc.)
"""
from fastapi import APIRouter, HTTPException, Body
from firebase_admin import auth, firestore
from pydantic import BaseModel, EmailStr

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str = "student" # Rôle par défaut

@router.post("/", status_code=201)
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


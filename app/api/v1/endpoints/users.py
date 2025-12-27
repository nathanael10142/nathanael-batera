"""
Routes pour la gestion des utilisateurs (création, etc.)
"""
from typing import List, Any
from fastapi import APIRouter, HTTPException, Body, Depends
from firebase_admin import auth, firestore
from pydantic import BaseModel, EmailStr
import secrets
import string

# Imports pour la sécurité et les modèles
from app.core.security import get_current_active_user, require_permission, Permissions
from app.schemas.user import User as UserSchema

router = APIRouter()

# Modèle pour la création, maintenant plus flexible
class UserCreate(BaseModel):
    email: EmailStr
    password: str | None = None # Le mot de passe est optionnel, on peut en générer un
    first_name: str | None = None
    last_name: str | None = None
    role: str = "student" # Rôle par défaut

# Modèle pour la mise à jour
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None
    is_active: bool | None = None

def generate_random_password(length: int = 12) -> str:
    """Génère un mot de passe aléatoire sécurisé."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for i in range(length))

@router.post("", status_code=201, summary="Create a new user")
async def create_user(user_in: UserCreate):
    """
    Créer un nouvel utilisateur dans Firebase Auth et un profil dans Firestore.I
    """
    try:
        # 1. Créer l'utilisateur dans Firebase Authentication
        user_record = auth.create_user(
            email=user_in.email,
            # Utiliser le mot de passe fourni ou en générer un
            password=user_in.password or generate_random_password(),
            display_name=f"{user_in.first_name or ''} {user_in.last_name or ''}".strip()
        )

        # 2. Créer un document de profil utilisateur dans Firestore
        db = firestore.client()
        full_name = f"{user_in.first_name or ''} {user_in.last_name or ''}".strip()
        user_profile_data = {
            "firebase_uid": user_record.uid, # Utiliser firebase_uid pour la cohérence
            "email": user_in.email,
            "display_name": full_name,
            "first_name": user_in.first_name,
            "last_name": user_in.last_name,
            "role": user_in.role,
            "created_at": firestore.SERVER_TIMESTAMP,
            "is_active": True,
        }
        db.collection("users").document(user_record.uid).set(user_profile_data, merge=True)

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

@router.get("", response_model=List[UserSchema], summary="List all users (Admin only)")
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
            # **CORRECTION : Mapper les champs de Firestore vers le schéma Pydantic**
            # Firestore a 'firebase_uid' et 'display_name', mais le schéma attend 'id' et 'username'.
            if user_data:
                mapped_data = {
                    "id": user_data.get("firebase_uid") or user_data.get("uid") or doc.id,
                    "username": user_data.get("display_name") or user_data.get("username") or "",
                    "email": user_data.get("email", ""),
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name"),
                    "role": user_data.get("role", "unknown"),
                    "is_active": user_data.get("is_active", True),
                }
                users_list.append(UserSchema(**mapped_data))
            
        return users_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching users: {e}")

@router.get("/{user_id}", response_model=UserSchema, summary="Get a single user by ID")
async def read_user(
    user_id: str,
    current_user: UserSchema = Depends(require_permission(Permissions.ADMIN_MANAGE_USERS))
):
    """Récupère les informations d'un utilisateur spécifique."""
    try:
        db = firestore.client()
        doc = db.collection("users").document(user_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = doc.to_dict()
        return UserSchema(
            id=doc.id,
            username=user_data.get("display_name", ""),
            email=user_data.get("email", ""),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            role=user_data.get("role", "unknown"),
            is_active=user_data.get("is_active", True),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching user: {e}")

@router.put("/{user_id}", response_model=UserSchema, summary="Update a user")
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    current_user: UserSchema = Depends(require_permission(Permissions.ADMIN_MANAGE_USERS))
) -> Any:
    """Met à jour les informations d'un utilisateur dans Firestore et Firebase Auth."""
    db = firestore.client()
    user_ref = db.collection("users").document(user_id)

    if not user_ref.get().exists:
        raise HTTPException(status_code=404, detail="User not found")

    # 1. Mettre à jour Firebase Auth
    auth_updates = {}
    if user_in.email:
        auth_updates["email"] = user_in.email
    if user_in.is_active is not None:
        auth_updates["disabled"] = not user_in.is_active
    
    full_name = f"{user_in.first_name or ''} {user_in.last_name or ''}".strip()
    if full_name:
        auth_updates["display_name"] = full_name

    if auth_updates:
        auth.update_user(user_id, **auth_updates)

    # 2. Mettre à jour Firestore
    firestore_updates = user_in.model_dump(exclude_unset=True)
    if full_name:
        firestore_updates["display_name"] = full_name
    user_ref.update(firestore_updates)

    # 3. Retourner l'utilisateur mis à jour
    updated_doc = user_ref.get()
    return await read_user(user_id, current_user)

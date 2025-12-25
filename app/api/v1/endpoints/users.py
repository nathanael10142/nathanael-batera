from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

# --- NOUVELLES IMPORTATIONS ---
from app.core.firebase import db # ✅ On importe la connexion à Firestore
from app.core.security import get_password_hash, get_current_active_user # On importe le hachage de mot de passe
from models import Utilisateur # On garde le modèle pour la dépendance get_current_active_user

router = APIRouter()

# --- NOUVEAUX MODÈLES PYDANTIC POUR FIRESTORE ---

class UserBase(BaseModel):
    """Modèle de base pour un utilisateur, utilisé pour la création."""
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str # ex: "student", "teacher", "admin"
    is_active: bool = True

class UserCreate(UserBase):
    """Modèle pour la création d'un utilisateur, inclut le mot de passe."""
    password: str

class UserInDB(UserBase):
    """Modèle représentant un utilisateur tel qu'il est stocké dans Firestore."""
    id: str # L'ID du document Firestore

@router.post("/", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    # current_admin: Utilisateur = Depends(get_current_active_user) # Sécurité: décommenter pour n'autoriser que les admins
):
    """
    Crée un nouvel utilisateur dans Firestore.
    Le nom d'utilisateur est utilisé comme ID de document.
    """
    if not db:
        raise HTTPException(status_code=503, detail="Connexion à la base de données non disponible.")

    user_ref = db.collection('users').document(user_in.username)
    if user_ref.get().exists:
        raise HTTPException(status_code=400, detail=f"Le nom d'utilisateur '{user_in.username}' existe déjà.")

    # Hacher le mot de passe avant de le stocker
    hashed_password = get_password_hash(user_in.password)
    
    # Préparer les données à stocker (sans le mot de passe en clair)
    user_data_to_store = user_in.model_dump()
    del user_data_to_store['password'] # Ne jamais stocker le mot de passe en clair
    user_data_to_store['hashed_password'] = hashed_password # Stocker la version hachée

    try:
        user_ref.set(user_data_to_store)
        # Préparer la réponse en ajoutant l'ID
        response_data = user_data_to_store.copy()
        response_data['id'] = user_in.username
        del response_data['hashed_password'] # Ne pas renvoyer le hash dans la réponse
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de l'utilisateur: {e}")


@router.get("/", response_model=List[UserInDB])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: Utilisateur = Depends(get_current_active_user),
) -> Any:
    """Récupère une liste d'utilisateurs depuis Firestore."""
    if not db:
        raise HTTPException(status_code=503, detail="Connexion à la base de données non disponible.")
    
    users_ref = db.collection('users').limit(limit).offset(skip).stream()
    users_list = []
    for user in users_ref:
        user_data = user.to_dict()
        user_data['id'] = user.id # Ajouter l'ID du document
        users_list.append(user_data)
    return users_list
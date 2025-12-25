from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# Ce modèle représente les données que nous stockons dans un document Firestore.
# Notez l'absence de mot de passe. Il ne doit JAMAIS être stocké en clair.
class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "student" # Rôle par défaut
    is_active: bool = True

    class Config:
        from_attributes = True # Permet de mapper depuis des objets

# Schéma pour la création d'un utilisateur.
# Il inclut le mot de passe qui sera traité par Firebase Auth.
class UserCreate(UserBase):
    password: str

# Schéma pour la mise à jour. Tous les champs sont optionnels.
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None # Pour mettre à jour le mot de passe

# Schéma pour lire un utilisateur depuis la base de données.
# Il inclut l'ID du document Firestore.
class UserInDB(UserBase):
    id: str = Field(..., alias="id")

# Schéma pour la réponse de l'API.
# C'est ce que le client Flutter recevra.
class User(UserInDB):
    pass
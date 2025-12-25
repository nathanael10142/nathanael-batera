"""
Schémas d'authentification
"""
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, field_validator


class Token(BaseModel):
    """Token d'accès"""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Payload du token"""
    sub: Optional[int] = None


class UserLogin(BaseModel):
    """Login utilisateur"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Réponse utilisateur"""
    id: int
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    role: Optional[str] = None
    faculty_id: Optional[int] = None
    
    class Config:
        from_attributes = True

    @field_validator("role", mode='before')
    @classmethod
    def get_role_name(cls, v: Any, info: Any) -> str:
        # 'v' est l'objet Role de la relation SQLAlchemy.
        # On vérifie simplement s'il existe et s'il a un attribut 'nom'.
        if v and hasattr(v, 'nom'):
            return v.nom
        return "N/A"  # Retourne "N/A" si le rôle n'est pas trouvé
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password, get_current_active_user
from app.schemas.token import Token
# from app.crud.crud_user import crud_user # Sera créé plus tard
from database import get_session
from models import Utilisateur # Temporaire, on utilisera le crud plus tard
from sqlalchemy.future import select
from sqlalchemy import or_

router = APIRouter()

@router.post("/login", response_model=Token, summary="User Login")
async def login_for_access_token(
    session: AsyncSession = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authentifie un utilisateur et retourne un token JWT.
    """
    # Remplacer par crud_user.get_by_email quand le CRUD sera implémenté
    # Recherche par email OU username
    result = await session.execute(
        select(Utilisateur).where(
            or_(Utilisateur.email == form_data.username, Utilisateur.nom_utilisateur == form_data.username)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.mot_de_passe):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(
        data={"sub": str(user.id)}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def read_users_me(current_user: Utilisateur = Depends(get_current_active_user)):
    """
    Récupère les informations de l'utilisateur connecté.
    """
    # On retourne un dictionnaire simple pour l'instant pour éviter les problèmes de sérialisation
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "is_active": current_user.is_active,
        # Pour tester les autres dashboards, changez "student" par "teacher" ou "accountant" ici
        # ou implémentez le chargement dynamique du rôle depuis la base de données
        "role": "student" 
    }
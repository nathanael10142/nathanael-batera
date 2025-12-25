"""
Sécurité : authentification, hashing, permissions
"""
from datetime import datetime, timedelta
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from database import get_session as get_db
from models import Utilisateur as User


# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier le mot de passe"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hasher le mot de passe"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Créer un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Obtenir l'utilisateur courant depuis le token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # user = await crud_user.get(db, id=int(user_id))
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Obtenir l'utilisateur actif"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def check_permission(user: User, permission: str) -> bool:
    """Vérifier si l'utilisateur a la permission"""
    if user.role and user.role.nom == "Admin":
        return True
    
    # Vérifier les permissions du rôle
    # if user.role and permission in [p.code for p in user.role.permissions]:
    #     return True
    
    return False


def require_permission(permission: str):
    """Décorateur pour vérifier les permissions"""
    async def permission_checker(current_user: User = Depends(get_current_active_user)):
        if not check_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return permission_checker


# Permissions standard
class Permissions:
    """Constantes des permissions"""
    # Admin
    ADMIN_FULL = "admin.full"
    ADMIN_CREATE_FACULTY = "admin.create_faculty"
    ADMIN_MANAGE_USERS = "admin.manage_users"
    
    # Academic
    ACADEMIC_VIEW = "academic.view"
    ACADEMIC_MANAGE = "academic.manage"
    ACADEMIC_ENCODE_NOTES = "academic.encode_notes"
    ACADEMIC_VALIDATE_NOTES = "academic.validate_notes"
    ACADEMIC_DELIBERATION = "academic.deliberation"
    
    # Financial
    FINANCIAL_VIEW = "financial.view"
    FINANCIAL_MANAGE = "financial.manage"
    FINANCIAL_PAYMENT = "financial.payment"
    FINANCIAL_AUDIT = "financial.audit"
    
    # Student
    STUDENT_VIEW_OWN = "student.view_own"
    STUDENT_MANAGE_OWN = "student.manage_own"
    
    # Communication
    COMMUNICATION_SEND = "communication.send"
    COMMUNICATION_OFFICIAL = "communication.official"
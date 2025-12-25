"""
Sécurité : authentification, hashing, permissions
"""
from datetime import datetime, timedelta
from typing import Optional, Any
from jose import JWTError, jwt as jose_jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth
from app.core.config import settings
# On importe le modèle de la base de données pour pouvoir le peupler
# avec les informations de Firebase et de notre propre base de données.
# Assurez-vous que le chemin d'importation est correct.
from app.models.user import User


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
    encoded_jwt = jose_jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> User: # 👈 CHANGEMENT: Nous allons renvoyer notre modèle User complet
    """Obtenir l'utilisateur courant depuis le token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # D'abord, décoder le token JWT que notre propre API a créé
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        firebase_uid: str = payload.get("sub")
        if firebase_uid is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Ensuite, nous allons chercher l'utilisateur dans notre propre base de données
    # en utilisant l'UID de Firebase comme identifiant.
    # Cela nous donne accès à ses rôles et permissions définis dans notre système.
    try:
        # NOTE: Cette partie suppose que vous avez une fonction pour récupérer un utilisateur
        # par son ID (qui serait le firebase_uid). Par exemple, `user_crud.get(id=firebase_uid)`.
        # Pour l'exemple, je vais simuler la création d'un objet User.
        # Dans une vraie application, vous le chargeriez depuis votre base de données.
        
        # Étape 1: Vérifier que l'utilisateur existe toujours dans Firebase
        firebase_user_record = auth.get_user(firebase_uid)

        # Étape 2: Charger l'utilisateur depuis votre base de données (à implémenter)
        # user = await crud.user.get(db, id=firebase_uid)
        # En attendant, on simule un utilisateur pour que la logique fonctionne
        user = User(id=firebase_user_record.uid, email=firebase_user_record.email, username=firebase_user_record.display_name, is_active=not firebase_user_record.disabled)
    except auth.UserNotFoundError: # L'utilisateur a été supprimé de Firebase
        raise credentials_exception
    
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
    """Vérifier si l'utilisateur a la permission (logique à implémenter)"""
    # La logique de permission dépendra de la structure de votre modèle `User` et `Role`.
    # Si `user.role` est une chaîne de caractères (ex: "admin", "teacher").
    # if user.role == "admin":
    if hasattr(user, 'role') and user.role and user.role.name == "admin": # Adapté pour un enum ou un objet avec un attribut `name`
        return True
    
    # Vérifier les permissions du rôle
    # if user.role and permission in [p.code for p in user.role.permissions]:
    #     return True
    
    return False


def require_permission(permission: str):
    """Décorateur pour vérifier les permissions"""
    async def permission_checker(current_user: User = Depends(get_current_active_user)):
        if not check_permission(current_user, permission): # Logique de permission à affiner
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
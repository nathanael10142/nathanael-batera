"""
Sécurité : authentification, hashing, permissions
"""
from datetime import datetime, timedelta
from typing import Optional, Any
from jose import JWTError, jwt as jose_jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth, firestore # 👈 Importer firestore
from app.core.config import settings
from types import SimpleNamespace


# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


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
) -> Any:
    """Obtenir l'utilisateur courant depuis le token. Retourne un objet léger.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    firebase_uid = None
    # First try: decode our local JWT
    try:
        try:
            if getattr(settings, 'DEBUG', False):
                token_preview = (token[:60] + '...') if token else '<empty>'
                print(f"🔍 Incoming token preview before decode: {token_preview}")

            payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if getattr(settings, 'DEBUG', False):
                # Print a compact summary (no secrets)
                print(f"🔓 JWT decoded successfully. keys={list(payload.keys())}, sub={payload.get('sub')}")
            firebase_uid = payload.get("sub")
            if firebase_uid is None:
                raise credentials_exception
        except JWTError as e:
            # Debug info to help diagnose decode failures in deployed env (do not print SECRET_KEY value)
            if getattr(settings, 'DEBUG', False):
                sk_len = len(settings.SECRET_KEY) if settings.SECRET_KEY else 0
                token_preview = (token[:40] + '...') if token else '<empty>'
                print(f"❌ JWT decode error: {e}; SECRET_KEY_len={sk_len}; ALGORITHM={settings.ALGORITHM}; token_preview={token_preview}")
            # Fallback: maybe the client accidentally sent a Firebase ID token instead of our local JWT.
            # Try to verify it as a Firebase id_token and recover the firebase_uid.
            try:
                if getattr(settings, 'DEBUG', False):
                    print('🔁 Attempting to verify incoming token as Firebase id_token...')
                firebase_claims = auth.verify_id_token(token)
                firebase_uid = firebase_claims.get('sub') or firebase_claims.get('user_id') or firebase_claims.get('uid')
                if getattr(settings, 'DEBUG', False):
                    print(f"✅ Firebase id_token verified as fallback. uid={firebase_uid}")
            except Exception as inner_e:
                if getattr(settings, 'DEBUG', False):
                    print(f"❌ verify_id_token fallback failed: {inner_e}")
                # Could not decode as local JWT and not a valid Firebase id_token -> unauthorized
                raise credentials_exception
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    # At this point we should have a firebase_uid
    if not firebase_uid:
        raise credentials_exception

    try:
        firebase_user_record = auth.get_user(firebase_uid)
        db = firestore.client()
        user_doc_ref = db.collection('users').document(firebase_uid)
        user_doc = user_doc_ref.get()

        # If user does not exist in Firestore, create a minimal record (helps first-login flows)
        if not user_doc.exists:
            email = getattr(firebase_user_record, 'email', None)
            display_name = getattr(firebase_user_record, 'display_name', '') or ''
            role = 'admin' if (email and email.lower() == 'nathanaelhacker6@gmail.com') else 'user'
            new_doc = {
                'firebase_uid': firebase_uid,
                'email': email,
                'display_name': display_name,
                'role': role,
                'created_at': firestore.SERVER_TIMESTAMP,
            }
            if getattr(settings, 'DEBUG', False):
                print(f"👤 Creating Firestore user for uid={firebase_uid}, email={email}, role={role}")
            user_doc_ref.set(new_doc)
            user_doc = user_doc_ref.get()
        else:
            if getattr(settings, 'DEBUG', False):
                print(f"✅ Existing Firestore user found for uid={firebase_uid}")

        user_data = user_doc.to_dict() or {}
        # Build a lightweight user object that contains needed attributes
        role_val = user_data.get('role') or user_data.get('role_name') or user_data.get('role_id')
        if isinstance(role_val, dict):
            role_name = role_val.get('name')
        else:
            role_name = role_val

        role_obj = SimpleNamespace(name=role_name) if role_name else None

        user = SimpleNamespace(
            id=str(firebase_user_record.uid),
            email=firebase_user_record.email,
            is_active=not getattr(firebase_user_record, 'disabled', False),
            role=role_obj,
            raw=user_data
        )

    except auth.UserNotFoundError:
        raise credentials_exception

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Any = Depends(get_current_user)
) -> Any:
    """Obtenir l'utilisateur actif"""
    if not getattr(current_user, 'is_active', False):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def check_permission(user: Any, permission: str) -> bool:
    """Vérifier si l'utilisateur a la permission (logique à implémenter)"""
    if hasattr(user, 'role') and user.role and getattr(user.role, 'name', None) == "admin":
        return True
    return False


def require_permission(permission: str):
    """Décorateur pour vérifier les permissions"""
    async def permission_checker(current_user: Any = Depends(get_current_active_user)):
        if not check_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return permission_checker


class Permissions:
    ADMIN_FULL = "admin.full"
    ADMIN_CREATE_FACULTY = "admin.create_faculty"
    ADMIN_MANAGE_USERS = "admin.manage_users"
    ACADEMIC_VIEW = "academic.view"
    ACADEMIC_MANAGE = "academic.manage"
    ACADEMIC_ENCODE_NOTES = "academic.encode_notes"
    ACADEMIC_VALIDATE_NOTES = "academic.validate_notes"
    ACADEMIC_DELIBERATION = "academic.deliberation"
    FINANCIAL_VIEW = "financial.view"
    FINANCIAL_MANAGE = "financial.manage"
    FINANCIAL_PAYMENT = "financial.payment"
    FINANCIAL_AUDIT = "financial.audit"
    STUDENT_VIEW_OWN = "student.view_own"
    STUDENT_MANAGE_OWN = "student.manage_own"
    COMMUNICATION_SEND = "communication.send"
    COMMUNICATION_OFFICIAL = "communication.official"
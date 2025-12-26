from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from firebase_admin import auth, firestore
from pydantic import BaseModel

from app.core.security import create_access_token, get_current_active_user # security depends on the SQLAlchemy model
from app.models.user import User as DBUser # Rename the SQLAlchemy model to avoid conflict
from app.schemas.user import User as UserSchema # Import the Pydantic schema


router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

class FirebaseLoginRequest(BaseModel):
    id_token: str

# NOTE: response_model removed to allow returning the created user alongside the token
@router.post("/login")
async def login_with_firebase(
    request: FirebaseLoginRequest
):
    """
    Authenticates with a Firebase ID token, creates a Firestore user on first login,
    and returns a local API access token plus a lightweight user summary.
    """
    try:
        # 1. Verify the Firebase ID token
        decoded_token = auth.verify_id_token(request.id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email')
        display_name = decoded_token.get('name') or decoded_token.get('displayName')

        # Debug log: verified incoming id_token
        from app.core.config import settings as _settings
        if getattr(_settings, 'DEBUG', False):
            print(f"🔐 [DEBUG] Firebase id_token verified for uid={uid}. Decoded keys={list(decoded_token.keys())}")

        # 2. Ensure a Firestore user document exists for this firebase UID
        db = firestore.client()
        users_ref = db.collection('users').document(uid)
        user_doc = users_ref.get()

        if not user_doc.exists:
            # Create the user document on first login
            user_record = {
                'firebase_uid': uid,
                'email': email,
                'display_name': display_name or (email.split('@')[0] if email else None),
                # Make the provided email an admin user
                'role': 'admin' if email == 'nathanaelhacker6@gmail.com' else 'user',
            }
            users_ref.set(user_record)
            if getattr(_settings, 'DEBUG', False):
                print(f"👤 [INFO] Created new Firestore user for uid={uid}, email={email}")
        else:
            user_record = user_doc.to_dict() or {}
            if getattr(_settings, 'DEBUG', False):
                print(f"✅ [INFO] Existing Firestore user found for uid={uid}")

        # 3. Create a local JWT access token for your API
        access_token = create_access_token(data={"sub": uid})
        if getattr(_settings, 'DEBUG', False):
            print(f"🔑 [DEBUG] Created local access token (truncated): {access_token[:20]}... (len={len(access_token)})")

        # Return token + lightweight user info
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "firebase_uid": uid,
                "email": user_record.get('email'),
                "display_name": user_record.get('display_name'),
                "role": user_record.get('role'),
            }
        }

    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during authentication: {e}",
        )


@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: DBUser = Depends(get_current_active_user)):
    """
    Get current user.
    """
    return current_user

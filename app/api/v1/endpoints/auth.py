from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from firebase_admin import auth
from pydantic import BaseModel

from app.core.security import create_access_token, get_current_active_user # security depends on the SQLAlchemy model
from app.models.user import User as DBUser # Rename the SQLAlchemy model to avoid conflict
from app.schemas.user_firebase import User as UserSchema # Import the Pydantic schema


router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

class FirebaseLoginRequest(BaseModel):
    id_token: str

@router.post("/login", response_model=Token)
async def login_with_firebase(
    request: FirebaseLoginRequest
):
    """
    Authenticates with a Firebase ID token and returns a local API access token.
    """
    try:
        # 1. Verify the Firebase ID token
        decoded_token = auth.verify_id_token(request.id_token)
        uid = decoded_token['uid']
        
        # 2. (Optional but recommended) Check if user exists in your local DB/Firestore
        # This step is already implicitly handled by get_current_user, but good to be aware of.
        # For now, we trust that if Firebase gives a valid token, the user is valid.

        # 3. Create a local JWT access token for your API
        # The 'sub' (subject) of your token will be the Firebase UID.
        access_token = create_access_token(data={"sub": uid})
        
        return {"access_token": access_token, "token_type": "bearer"}

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

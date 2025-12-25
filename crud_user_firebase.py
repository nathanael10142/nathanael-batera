from google.cloud.firestore import Client as FirestoreClient
from firebase_admin import auth
from typing import List, Dict, Any, Optional

from app.schemas.user import UserCreate, UserUpdate

COLLECTION_NAME = "users"

def create_user(db: FirestoreClient, user_in: UserCreate) -> Dict[str, Any]:
    """
    Crée un utilisateur dans Firebase Auth et son document correspondant dans Firestore.
    """
    # 1. Créer l'utilisateur dans Firebase Authentication
    firebase_user = auth.create_user(
        email=user_in.email,
        password=user_in.password,
        display_name=user_in.username,
        disabled=not user_in.is_active
    )
    
    # 2. Préparer les données pour Firestore (sans le mot de passe)
    user_data = user_in.model_dump(exclude={"password"})
    
    # 3. Créer le document dans Firestore avec l'UID de Firebase Auth comme ID
    db.collection(COLLECTION_NAME).document(firebase_user.uid).set(user_data)
    
    # 4. Retourner les données avec l'ID
    return {"id": firebase_user.uid, **user_data}

def get_user(db: FirestoreClient, user_id: str) -> Optional[Dict[str, Any]]:
    """Récupère un utilisateur par son ID (UID)."""
    doc_ref = db.collection(COLLECTION_NAME).document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}
    return None

def get_all_users(db: FirestoreClient) -> List[Dict[str, Any]]:
    """Récupère tous les utilisateurs."""
    users_ref = db.collection(COLLECTION_NAME).stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in users_ref]

def update_user(db: FirestoreClient, user_id: str, user_in: UserUpdate) -> Optional[Dict[str, Any]]:
    """Met à jour un utilisateur."""
    # Mettre à jour Firebase Auth
    auth_update_data = {}
    if user_in.email: auth_update_data['email'] = user_in.email
    if user_in.password: auth_update_data['password'] = user_in.password
    if user_in.is_active is not None: auth_update_data['disabled'] = not user_in.is_active
    if auth_update_data:
        auth.update_user(user_id, **auth_update_data)

    # Mettre à jour Firestore
    firestore_data = user_in.model_dump(exclude_unset=True, exclude={"password"})
    if firestore_data:
        db.collection(COLLECTION_NAME).document(user_id).update(firestore_data)
    
    return get_user(db, user_id)

def delete_user(db: FirestoreClient, user_id: str) -> bool:
    """Supprime un utilisateur de Auth et Firestore."""
    auth.delete_user(user_id)
    db.collection(COLLECTION_NAME).document(user_id).delete()
    return True
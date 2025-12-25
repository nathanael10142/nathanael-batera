import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client as FirestoreClient
import os
import json

from app.core.config import settings

def initialize_firebase():
    """
    Initializes the Firebase Admin SDK using credentials from environment variables.
    """
    try:
        # Vérifie si l'app est déjà initialisée pour éviter les erreurs au rechargement
        firebase_admin.get_app()
        print("Firebase app already initialized.")
    except ValueError:
        print("Initializing Firebase app...")
        # Pour Render, il est plus simple de stocker le contenu du JSON dans une seule variable d'environnement.
        firebase_creds_json_str = os.getenv("FIREBASE_CREDENTIALS_JSON")
        
        if not firebase_creds_json_str:
            raise ValueError("La variable d'environnement FIREBASE_CREDENTIALS_JSON n'est pas définie.")

        cred_json = json.loads(firebase_creds_json_str)
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase app initialized successfully.")

def get_firestore_client() -> FirestoreClient:
    """FastAPI dependency to get a Firestore client instance."""
    return firestore.client()
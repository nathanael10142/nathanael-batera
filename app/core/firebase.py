import firebase_admin
from firebase_admin import credentials, firestore
from .config import settings
import os

db = None

def initialize_firebase():
    """
    Initialise la connexion à Firebase Admin SDK en utilisant les credentials
    stockés dans une variable d'environnement.
    """
    global db
    try:
        # La meilleure pratique est de stocker le JSON des credentials dans une variable d'environnement
        cred_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("🔥 Connexion à Firestore réussie.")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de Firebase: {e}")
        db = None
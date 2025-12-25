import asyncio
import sys
import os

# Ajout du dossier courant au path pour trouver 'app'
sys.path.append(os.getcwd())

from firebase_admin import auth, firestore
from app.core.security import get_password_hash

async def create_user():
    """
    Create an admin user in Firebase Auth and a profile in Firestore.
    """
    email = "nathanaelhacker6@gmail.com"
    plain_password = "nathanael1209ba"

    print(f"Vérification de l'existence de l'utilisateur : {email}")

    try:
        # Try to find user in Firebase Auth
        try:
            user_record = auth.get_user_by_email(email)
            print("L'utilisateur existe déjà dans Firebase Auth. Mise à jour du mot de passe.")
            auth.update_user(user_record.uid, password=plain_password)
        except auth.UserNotFoundError:
            print("Création de l'utilisateur dans Firebase Auth...")
            user_record = auth.create_user(email=email, password=plain_password, display_name="Admin")

        # Create profile document in Firestore
        db = firestore.client()
        profile = {
            "uid": user_record.uid,
            "email": email,
            "display_name": "Admin",
            "role": "admin",
            "created_at": firestore.SERVER_TIMESTAMP
        }
        db.collection("users").document(user_record.uid).set(profile)

        print("✅ Utilisateur admin créé/mis à jour avec succès dans Firebase et Firestore.")
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_user())
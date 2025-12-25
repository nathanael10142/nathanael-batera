import asyncio
import sys
import os

# Ajout du dossier courant au path pour trouver 'app'
sys.path.append(os.getcwd())

from firebase_admin import auth, firestore
from app.core.security import get_password_hash

async def create_data():
    print("--- Démarrage du script de création (Firestore) ---")

    db = firestore.client()

    # 1. Créer le rôle 'student' : dans Firestore on peut stocker roles dans une collection
    role_docs = list(db.collection('roles').where('name','==','Etudiant').limit(1).stream())
    if not role_docs:
        print("Création du rôle 'Etudiant'...")
        db.collection('roles').document().set({'name': 'Etudiant', 'code': 'student'})
    else:
        print("Le rôle 'Etudiant' existe déjà dans Firestore.")

    # 2. Créer l'utilisateur de test
    email = "etudiant@univ.com"
    username = "etudiant"
    password = "password123"

    try:
        user_record = auth.get_user_by_email(email)
        print("Utilisateur test déjà présent dans Firebase Auth.")
    except auth.UserNotFoundError:
        print(f"Création de l'utilisateur {email} dans Firebase Auth...")
        user_record = auth.create_user(email=email, password=password, display_name=username)

    # Create profile doc
    profile_ref = db.collection('users').document(user_record.uid)
    profile_doc = profile_ref.get()
    if not profile_doc.exists:
        profile_ref.set({
            'uid': user_record.uid,
            'email': email,
            'username': username,
            'role': 'student',
            'created_at': firestore.SERVER_TIMESTAMP
        })
        print('✅ Utilisateur créé avec succès dans Firestore.')
    else:
        print('ℹ️ Profil utilisateur déjà existant dans Firestore.')

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_data())
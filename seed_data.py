import asyncio
import sys
import os

sys.path.append(os.getcwd())

from firebase_admin import auth, firestore
from app.core.security import get_password_hash

COMMON_PASSWORD = "nathanael1209ba"

async def seed_database():
    db = firestore.client()
    print("🚀 Démarrage du peuplement Firestore (ADMIN UNIQUE)...")

    # Roles
    roles = ["Admin", "Etudiant", "Enseignant", "Comptable", "Doyen"]
    for r in roles:
        docs = list(db.collection('roles').where('name','==',r).limit(1).stream())
        if not docs:
            db.collection('roles').document().set({'name': r})

    # Admin
    admin_email = "nathanaelhacker6@gmail.com"
    try:
        user_record = auth.get_user_by_email(admin_email)
        print('Admin déjà présent dans Firebase Auth')
    except auth.UserNotFoundError:
        user_record = auth.create_user(email=admin_email, password=COMMON_PASSWORD, display_name='Admin')
        print('Admin créé dans Firebase Auth')

    # Profile
    profile_ref = db.collection('users').document(user_record.uid)
    profile_ref.set({
        'uid': user_record.uid,
        'email': admin_email,
        'role': 'Admin',
        'created_at': firestore.SERVER_TIMESTAMP
    })

    print('✅ Seed Firestore terminé')

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_database())
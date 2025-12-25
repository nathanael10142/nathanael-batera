import asyncio
import sys
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ajout du dossier courant au path pour trouver les modules
sys.path.append(os.getcwd())

from app.core.security import get_password_hash
from database import async_session
from models import Utilisateur, Role

async def create_user():
    """
    Crée un nouvel utilisateur dans la base de données avec un mot de passe correctement haché.
    """
    email = "nathanaelhacker6@gmail.com"
    plain_password = "nathanael1209ba"

    print(f"Vérification de l'existence de l'utilisateur : {email}")
    
    db: AsyncSession = async_session()
    try:
        # 1. Trouver le rôle "Admin"
        result_role = await db.execute(select(Role).where(Role.nom == "Admin"))
        admin_role = result_role.scalar_one_or_none()

        if not admin_role:
            print("❌ ERREUR: Le rôle 'Admin' n'a pas été trouvé. Veuillez d'abord lancer le script seed_data.py.")
            return

        print(f"Rôle 'Admin' trouvé avec l'ID: {admin_role.id}")

        # Vérifier si l'utilisateur existe déjà
        result = await db.execute(select(Utilisateur).where(Utilisateur.email == email))
        existing_user = result.scalars().first()

        if existing_user:
            print(f"L'utilisateur {email} existe déjà. Mise à jour du mot de passe et du rôle.")
            existing_user.mot_de_passe = get_password_hash(plain_password)
            existing_user.role_id = admin_role.id
            print("Mot de passe haché et mis à jour.")
        else:
            print(f"L'utilisateur {email} n'existe pas. Création en cours...")
            # Créer un nouvel utilisateur
            hashed_password = get_password_hash(plain_password)
            new_user = Utilisateur(
                email=email,
                nom_utilisateur=email.split('@')[0],
                mot_de_passe=hashed_password,
                actif=True,
                role_id=admin_role.id
            )
            db.add(new_user)
            print("Nouvel utilisateur créé avec un mot de passe haché.")

        await db.commit()
        print("✅ Opération terminée avec succès.")
    finally:
        await db.close()

if __name__ == "__main__":
    # Fix pour Windows et asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_user())
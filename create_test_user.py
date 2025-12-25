import asyncio
import sys
import os

# Ajout du dossier courant au path pour trouver 'app', 'database', etc.
sys.path.append(os.getcwd())

from sqlalchemy import select
from database import async_session
from models import Utilisateur, Role
from app.core.security import get_password_hash

async def create_data():
    async with async_session() as session:
        print("--- Démarrage du script de création ---")

        # 1. Créer le rôle 'student'
        result = await session.execute(select(Role).where(Role.nom == "Etudiant"))
        role = result.scalar_one_or_none()
        
        if not role:
            print("Création du rôle 'Etudiant'...")
            role = Role(nom="Etudiant")
            session.add(role)
            await session.commit()
            await session.refresh(role)
        else:
            print("Le rôle 'student' existe déjà.")

        # 2. Créer l'utilisateur
        email = "etudiant@univ.com"
        username = "etudiant"
        password = "password123"
        
        result = await session.execute(select(Utilisateur).where(Utilisateur.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"Création de l'utilisateur {email}...")
            user = Utilisateur(
                email=email,
                nom_utilisateur=username,
                mot_de_passe=get_password_hash(password),
                actif=True,
                role_id=role.id
            )
            session.add(user)
            await session.commit()
            print("✅ Utilisateur créé avec succès !")
            print(f"👉 Login    : {username} (ou {email})")
            print(f"👉 Password : {password}")
        else:
            print(f"ℹ️ L'utilisateur {email} existe déjà.")

if __name__ == "__main__":
    # Fix pour Windows et asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(create_data())
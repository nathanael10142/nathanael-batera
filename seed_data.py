import asyncio
import sys
import os
import random
from datetime import date, datetime, timedelta

# Ajout du dossier courant au path
sys.path.append(os.getcwd())

from sqlalchemy import select
from database import async_session
from models import (
    Universite, Faculte, Departement, OptionFiliere, Promotion, Groupe,
    Etudiant, Enseignant, Utilisateur, Role, UE, EtudiantUE, Paiement, Document,
    CycleType, StatutAcademique, StatutFinancier, TypeUE, StatutUE, ModePaiement, StatutPaiement, TypeDocument
)
from app.core.security import get_password_hash

# Configuration Globale
COMMON_PASSWORD = "nathanael1209ba"
HASHED_PASSWORD = get_password_hash(COMMON_PASSWORD)

async def seed_database():
    async with async_session() as session:
        print("🚀 Démarrage du peuplement (ADMIN UNIQUE)...")

        # 1. Création des Rôles
        roles = ["Admin", "Etudiant", "Enseignant", "Comptable", "Doyen"]
        db_roles = {}
        for r_name in roles:
            res = await session.execute(select(Role).where(Role.nom == r_name))
            role = res.scalar_one_or_none()
            if not role:
                role = Role(nom=r_name)
                session.add(role)
            db_roles[r_name] = role
        await session.commit()
        
        # Rafraîchir pour avoir les IDs
        for r_name in roles:
            await session.refresh(db_roles[r_name])

        # 2. Création de l'ADMIN SUPRÊME
        admin_email = "nathanaelhacker6@gmail.com"
        res = await session.execute(select(Utilisateur).where(Utilisateur.email == admin_email))
        admin_user = res.scalar_one_or_none()
        if not admin_user:
            print(f"👑 Création de l'Admin Suprême : {admin_email}")
            admin_user = Utilisateur(
                nom_utilisateur="admin_supreme",
                email=admin_email,
                mot_de_passe=HASHED_PASSWORD,
                role_id=db_roles["Admin"].id,
                actif=True
            )
            session.add(admin_user)
            await session.commit()

        print(f"✅ Admin créé avec succès !")
        print(f"🔑 Mot de passe UNIQUE pour tous: {COMMON_PASSWORD}")
        print(f"👤 Admin: {admin_email}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_database())
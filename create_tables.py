# c:\Users\HP\Desktop\university-system\backend\create_tables.py
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv, find_dotenv

# Ajoute le répertoire du projet au chemin Python pour trouver les modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- C'est ici que la magie opère ---
# 1. Importer la Base et tous les modèles depuis les bons fichiers
from database import Base
from models import Utilisateur, Role # Importer les modèles directement

# 3. Importer les utilitaires de sécurité pour hacher le mot de passe
from app.core.security import get_password_hash


print("Script de création de tables démarré.")

# 3. Charger les variables d'environnement du fichier .env
# Force la lecture du fichier .env en UTF-8
load_dotenv(find_dotenv(), encoding='utf-8')
DATABASE_URL = os.getenv("DATABASE_URL_SYNC")

if not DATABASE_URL:
    print("❌ ERREUR: La variable d'environnement DATABASE_URL_SYNC n'est pas définie dans votre fichier .env.")
    sys.exit(1)

print(f"Connexion à la base de données...")

try:
    # 4. Créer un moteur de base de données synchrone
    engine = create_engine(
        DATABASE_URL,
        client_encoding='utf8' # ✅ Force l'encodage UTF-8 pour la connexion
    )

    # 5. Créer une session pour interagir avec la base de données
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # 6. Créer toutes les tables
    print("Création des tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Succès ! Toutes les tables ont été créées.")

    # 7. Créer l'utilisateur administrateur
    print("\nVérification de l'utilisateur administrateur...")
    admin_email = "nathanaelhacker6@gmail.com"
    admin_user = db.query(Utilisateur).filter(Utilisateur.email == admin_email).first()

    if not admin_user:
        print(f"L'utilisateur '{admin_email}' n'existe pas. Création en cours...")
        hashed_password = get_password_hash("nathanael1209ba")
        
        # Récupérer le rôle 'admin'
        admin_role = db.query(Role).filter(Role.nom == "admin").one()

        new_admin = Utilisateur(
            nom_utilisateur="admin",
            email=admin_email,
            mot_de_passe=hashed_password,
            role_id=admin_role.id,
            actif=True,
        )
        db.add(new_admin)
        db.commit()
        print("✅ Utilisateur administrateur créé avec succès !")
    else:
        print("👍 L'utilisateur administrateur existe déjà. Aucune action requise.")

    db.close()
    print("\n🚀 Initialisation de la base de données terminée.")

except Exception as e:
    print(f"❌ Une erreur est survenue : {e}")
    if 'db' in locals() and db.is_active:
        db.close()
    sys.exit(1)

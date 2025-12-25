# c:\Users\HP\Desktop\university-system\backend\create_tables.py
import os
import sys

# Ajoute le répertoire du projet au chemin Python pour trouver les modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from firebase_admin import firestore

print("Ce script n'utilise plus SQL. Il crée des collections de démonstration dans Firestore si nécessaire.")

db = firestore.client()

# Créer une collection 'roles' si elle n'existe pas
roles = ['Admin', 'Etudiant', 'Enseignant', 'Comptable', 'Doyen']
for r in roles:
    docs = list(db.collection('roles').where('name','==',r).limit(1).stream())
    if not docs:
        db.collection('roles').document().set({'name': r})

print('✅ Structure Firestore minimale créée (roles).')

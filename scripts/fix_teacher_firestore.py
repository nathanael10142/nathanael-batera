"""
Script pour vérifier et corriger les données d'un enseignant dans Firestore
"""
import firebase_admin
from firebase_admin import credentials, firestore

# Initialise Firebase (utilise ton fichier de clé service account)
cred = credentials.Certificate('../app/serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

teacher_id = 'anOpyMv3b5hufHXByfgF3xbuX6T2'

def ensure_teacher_doc():
    ref = db.collection('teachers').document(teacher_id)
    doc = ref.get()
    if doc.exists:
        data = doc.to_dict()
        print('Données actuelles:', data)
    else:
        print('Document enseignant absent, création...')
        data = {}
    # Corrige ou complète les champs
    data.update({
        'full_name': 'Rubaka Patient',
        'first_name': 'Rubaka',
        'last_name': 'Patient',
        'department': 'Informatique',
        'faculty': 'Sciences',
        'status': 'active',
        'academic_year': '2025-2026',
        'photo_url': '',
    })
    ref.set(data, merge=True)
    print('Document enseignant mis à jour.')

if __name__ == '__main__':
    ensure_teacher_doc()

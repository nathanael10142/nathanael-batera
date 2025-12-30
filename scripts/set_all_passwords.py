"""
Script pour mettre à jour le mot de passe de tous les utilisateurs (enseignants et étudiants) dans Firestore.
Le mot de passe sera 'nathanael1209ba' pour tous.
"""
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('../app/serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

NEW_PASSWORD = 'nathanael1209ba'

# Met à jour le champ 'password' pour tous les enseignants
def update_teachers_password():
    teachers = db.collection('teachers').stream()
    for t in teachers:
        db.collection('teachers').document(t.id).update({'password': NEW_PASSWORD})
    print('Mot de passe mis à jour pour tous les enseignants.')

# Met à jour le champ 'password' pour tous les étudiants
def update_students_password():
    students = db.collection('students').stream()
    for s in students:
        db.collection('students').document(s.id).update({'password': NEW_PASSWORD})
    print('Mot de passe mis à jour pour tous les étudiants.')

if __name__ == '__main__':
    update_teachers_password()
    update_students_password()
    print('Tous les mots de passe ont été mis à jour.')

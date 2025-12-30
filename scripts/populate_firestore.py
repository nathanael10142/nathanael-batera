"""
Script avancé pour peupler Firestore avec beaucoup de données réalistes et structurées :
- 5 facultés, 2 départements/faculté, 5 filières/département, 2 promotions/filière
- 50 enseignants, 50 étudiants, 100 UE, inscriptions, notes, examens, notifications
- Toutes les relations sont respectées (chaque UE liée à une filière, promotion, département, faculté, enseignant)
"""
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta

cred = credentials.Certificate('../app/serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

N_FACULTIES = 5
N_DEPARTMENTS = 2
N_FILIERES = 5  # 5 filières par département
N_PROMOS = 2
N_UE_PER_PROMO = 5
N_TEACHERS = 50
N_STUDENTS = 50
N_EXAMS = 30
N_NOTIFICATIONS = 30

faculties = []
departments = []
filieres = []
promos = []
teachers = []
students = []
ues = []

# 1. Facultés, départements, filières, promotions
def create_structure():
    faculties.clear()
    departments.clear()
    filieres.clear()
    promos.clear()
    for f in range(N_FACULTIES):
        fac_id = f"fac_{f+1}"
        fac_name = f"Faculté {f+1}"
        faculties.append({'id': fac_id, 'name': fac_name})
        db.collection('faculties').document(fac_id).set({'id': fac_id, 'name': fac_name})
        for d in range(N_DEPARTMENTS):
            dep_id = f"dep_{f+1}_{d+1}"
            dep_name = f"Département {d+1} de {fac_name}"
            departments.append({'id': dep_id, 'name': dep_name, 'faculty_id': fac_id})
            db.collection('departments').document(dep_id).set({'id': dep_id, 'name': dep_name, 'faculty_id': fac_id})
            for fi in range(N_FILIERES):
                fil_id = f"fil_{f+1}_{d+1}_{fi+1}"
                fil_name = f"Filière {fi+1} de {dep_name}"
                filieres.append({'id': fil_id, 'name': fil_name, 'department_id': dep_id, 'faculty_id': fac_id})
                db.collection('filieres').document(fil_id).set({'id': fil_id, 'name': fil_name, 'department_id': dep_id, 'faculty_id': fac_id})
                for p in range(N_PROMOS):
                    promo_id = f"promo_{f+1}_{d+1}_{fi+1}_{p+1}"
                    promo_name = f"Promotion {p+1} de {fil_name}"
                    promos.append({'id': promo_id, 'name': promo_name, 'filiere_id': fil_id, 'department_id': dep_id, 'faculty_id': fac_id})
                    db.collection('promotions').document(promo_id).set({'id': promo_id, 'name': promo_name, 'filiere_id': fil_id, 'department_id': dep_id, 'faculty_id': fac_id})
    print(f"Créé {len(faculties)} facultés, {len(departments)} départements, {len(filieres)} filières, {len(promos)} promotions.")

# 2. Enseignants
def create_teachers():
    teachers.clear()
    for i in range(N_TEACHERS):
        tid = f"teacher_{i+1}"
        teachers.append(tid)
        fac = random.choice(faculties)
        dep = random.choice([d for d in departments if d['faculty_id'] == fac['id']])
        fil = random.choice([f for f in filieres if f['department_id'] == dep['id']])
        db.collection('teachers').document(tid).set({
            'full_name': f'Professeur {i+1}',
            'first_name': f'Prenom{i+1}',
            'last_name': f'Nom{i+1}',
            'email': f'enseignant{i+1}@univ.com',
            'phone': f'+24389000{i+1:03d}',
            'gender': random.choice(['Homme', 'Femme']),
            'birthdate': (datetime(1980, 1, 1) + timedelta(days=random.randint(0, 10000))).strftime('%Y-%m-%d'),
            'role': 'teacher',
            'department': dep['name'],
            'department_id': dep['id'],
            'faculty': fac['name'],
            'faculty_id': fac['id'],
            'filiere': fil['name'],
            'filiere_id': fil['id'],
            'status': 'active',
            'academic_year': '2025-2026',
            'photo_url': '',
            'password': 'nathanael1209ba',
        })
    print(f"Créé {N_TEACHERS} enseignants.")

# 3. Étudiants
def create_students():
    students.clear()
    for i in range(N_STUDENTS):
        sid = f"student_{i+1}"
        students.append(sid)
        promo = random.choice(promos)
        fil = [f for f in filieres if f['id'] == promo['filiere_id']][0]
        dep = [d for d in departments if d['id'] == promo['department_id']][0]
        fac = [f for f in faculties if f['id'] == promo['faculty_id']][0]
        db.collection('students').document(sid).set({
            'full_name': f'Étudiant {i+1}',
            'first_name': f'PrenomE{i+1}',
            'last_name': f'NomE{i+1}',
            'email': f'etudiant{i+1}@univ.com',
            'phone': f'+24399000{i+1:03d}',
            'gender': random.choice(['Homme', 'Femme']),
            'birthdate': (datetime(2000, 1, 1) + timedelta(days=random.randint(0, 9000))).strftime('%Y-%m-%d'),
            'role': 'student',
            'promotion': promo['name'],
            'promotion_id': promo['id'],
            'filiere': fil['name'],
            'filiere_id': fil['id'],
            'department': dep['name'],
            'department_id': dep['id'],
            'faculty': fac['name'],
            'faculty_id': fac['id'],
            'status': 'active',
            'academic_year': '2025-2026',
            'photo_url': '',
            'password': 'nathanael1209ba',
        })
    print(f"Créé {N_STUDENTS} étudiants.")

# 4. UE (cours)
def create_ues():
    for promo in promos:
        for i in range(N_UE_PER_PROMO):
            ue_id = f"ue_{promo['id']}_{i+1}"
            ues.append(ue_id)
            fil = [f for f in filieres if f['id'] == promo['filiere_id']][0]
            dep = [d for d in departments if d['id'] == promo['department_id']][0]
            fac = [f for f in faculties if f['id'] == promo['faculty_id']][0]
            teacher_id = random.choice(teachers)
            db.collection('ues').document(ue_id).set({
                'id': ue_id,
                'title': f'UE {i+1} {promo["name"]}',
                'code': f'UE{random.randint(100,999)}',
                'teacher_id': teacher_id,
                'promotion': promo['name'],
                'promotion_id': promo['id'],
                'filiere': fil['name'],
                'filiere_id': fil['id'],
                'department': dep['name'],
                'department_id': dep['id'],
                'faculty': fac['name'],
                'faculty_id': fac['id'],
                'academic_year': '2025-2026',
            })
    print(f"Créé {len(ues)} UE (cours).")

# 5. Inscriptions
def create_enrollments():
    for ue_id in ues:
        promo_id = db.collection('ues').document(ue_id).get().to_dict()['promotion_id']
        promo_students = [s for s in students if db.collection('students').document(s).get().to_dict()['promotion_id'] == promo_id]
        enrolled = random.sample(promo_students, k=min(10, len(promo_students)))
        for sid in enrolled:
            db.collection('enrollments').add({
                'ue_id': ue_id,
                'student_id': sid,
                'academic_year': '2025-2026',
            })
    print("Inscriptions créées.")

# 6. Notes
def create_grades():
    for ue_id in ues:
        enrolled = db.collection('enrollments').where('ue_id', '==', ue_id).stream()
        for enr in enrolled:
            sid = enr.to_dict()['student_id']
            for t in ['exam', 'cc']:
                db.collection('grades').add({
                    'ue_id': ue_id,
                    'student_id': sid,
                    'grade': round(random.uniform(5, 18), 2),
                    'type': t,
                    'session': '2025',
                    'validated': random.choice([True, False]),
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'updated_by': random.choice(teachers),
                })
    print("Notes créées.")

# 7. Examens
def create_exams():
    for i in range(N_EXAMS):
        ue_id = random.choice(ues)
        teacher_id = db.collection('ues').document(ue_id).get().to_dict()['teacher_id']
        exam_date = datetime.utcnow() + timedelta(days=random.randint(1, 60))
        db.collection('exams').add({
            'ue_id': ue_id,
            'teacher_id': teacher_id,
            'date': exam_date.isoformat(),
            'title': f'Examen {i+1}',
        })
    print(f"Créé {N_EXAMS} examens.")

# 8. Notifications
def create_notifications():
    for i in range(N_NOTIFICATIONS):
        teacher_id = random.choice(teachers)
        db.collection('notifications').add({
            'recipient_teacher_id': teacher_id,
            'title': f'Notification {i+1}',
            'body': f'Ceci est la notification {i+1}',
            'created_at': firestore.SERVER_TIMESTAMP,
        })
    print(f"Créé {N_NOTIFICATIONS} notifications.")

if __name__ == '__main__':
    create_structure()
    create_teachers()
    create_students()
    create_ues()
    create_enrollments()
    create_grades()
    create_exams()
    create_notifications()
    print("Population avancée de la base Firestore terminée !")

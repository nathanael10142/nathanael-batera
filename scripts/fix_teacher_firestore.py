"""
Script pour vérifier et corriger les données d'un enseignant dans Firestore
"""
import firebase_admin
from firebase_admin import credentials, firestore, auth
import random
import string
from datetime import datetime

# Initialise Firebase (utilise ton fichier de clé service account)
cred = credentials.Certificate('../app/serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

teacher_id = 'anOpyMv3b5hufHXByfgF3xbuX6T2'

RESET_COLLECTIONS = [
    'faculties', 'departments', 'programs', 'promotions', 'ues',
    'students', 'teachers', 'admins', 'users', 'groups'
]

TEST_PASSWORD = 'nathanael1209ba'
ADMIN_EMAIL = 'nathanaelhacker6@gmail.com'

# --- Suppression de toutes les collections ---
def delete_all_collections():
    for col in RESET_COLLECTIONS:
        print(f'Suppression de la collection {col}...')
        docs = db.collection(col).stream()
        for doc in docs:
            db.collection(col).document(doc.id).delete()
    print('Toutes les collections ont été supprimées.')

# --- Génération d'un identifiant unique ---
def gen_id(prefix):
    return prefix + '_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

# --- Génération de la date actuelle ---
def now():
    return datetime.now().isoformat()

# --- Création des entités (à compléter ensuite) ---
def create_university_structure():
    # --- Facultés, départements, filières, promotions, UEs ---
    faculties = [
        {'name': 'Sciences', 'code': 'SCI'},
        {'name': 'Lettres et Sciences Humaines', 'code': 'LSH'},
        {'name': 'Droit', 'code': 'DRT'},
        {'name': 'Médecine', 'code': 'MED'},
        {'name': 'Sciences Économiques et de Gestion', 'code': 'SEG'},
    ]
    departments_by_faculty = {
        'SCI': [
            {'name': 'Informatique', 'code': 'INFO'},
            {'name': 'Mathématiques', 'code': 'MATH'},
            {'name': 'Physique', 'code': 'PHYS'},
        ],
        'LSH': [
            {'name': 'Philosophie', 'code': 'PHILO'},
            {'name': 'Histoire', 'code': 'HIST'},
        ],
        'DRT': [
            {'name': 'Droit Privé', 'code': 'DPRV'},
            {'name': 'Droit Public', 'code': 'DPUB'},
        ],
        'MED': [
            {'name': 'Médecine Générale', 'code': 'MEDG'},
            {'name': 'Pharmacie', 'code': 'PHAR'},
        ],
        'SEG': [
            {'name': 'Gestion', 'code': 'GEST'},
            {'name': 'Économie', 'code': 'ECO'},
        ],
    }
    programs_by_department = {
        'INFO': [
            {'name': 'Génie Logiciel', 'code': 'GL'},
            {'name': 'Réseaux et Télécoms', 'code': 'RT'},
        ],
        'MATH': [
            {'name': 'Mathématiques Fondamentales', 'code': 'MF'},
        ],
        'PHYS': [
            {'name': 'Physique Appliquée', 'code': 'PA'},
        ],
        'PHILO': [
            {'name': 'Philosophie Générale', 'code': 'PG'},
        ],
        'HIST': [
            {'name': 'Histoire Moderne', 'code': 'HM'},
        ],
        'DPRV': [
            {'name': 'Droit Civil', 'code': 'DC'},
        ],
        'DPUB': [
            {'name': 'Droit Constitutionnel', 'code': 'DCO'},
        ],
        'MEDG': [
            {'name': 'Médecine', 'code': 'MED'},
        ],
        'PHAR': [
            {'name': 'Pharmacie', 'code': 'PHAR'},
        ],
        'GEST': [
            {'name': 'Gestion des Entreprises', 'code': 'GE'},
        ],
        'ECO': [
            {'name': 'Économie Appliquée', 'code': 'EA'},
        ],
    }
    promotions = [
        {'name': 'L1', 'code': 'L1'},
        {'name': 'L2', 'code': 'L2'},
        {'name': 'L3', 'code': 'L3'},
        {'name': 'M1', 'code': 'M1'},
        {'name': 'M2', 'code': 'M2'},
    ]
    # --- Création des entités ---
    faculty_ids = {}
    department_ids = {}
    program_ids = {}
    promotion_ids = {}
    ue_ids = {}
    # Facultés
    for fac in faculties:
        fac_id = gen_id('fac')
        faculty_ids[fac['code']] = fac_id
        db.collection('faculties').document(fac_id).set({
            'id': fac_id,
            'name': fac['name'],
            'code': fac['code'],
            'created_at': now(),
            'updated_at': now(),
        })
    # Départements
    for fac_code, deps in departments_by_faculty.items():
        for dep in deps:
            dep_id = gen_id('dep')
            department_ids[dep['code']] = dep_id
            db.collection('departments').document(dep_id).set({
                'id': dep_id,
                'name': dep['name'],
                'code': dep['code'],
                'faculty_id': faculty_ids[fac_code],
                'created_at': now(),
                'updated_at': now(),
            })
    # Programmes
    for dep_code, progs in programs_by_department.items():
        for prog in progs:
            prog_id = gen_id('prog')
            program_ids[prog['code']] = prog_id
            db.collection('programs').document(prog_id).set({
                'id': prog_id,
                'name': prog['name'],
                'code': prog['code'],
                'department_id': department_ids[dep_code],
                'created_at': now(),
                'updated_at': now(),
            })
    # Promotions
    for prog_code, prog_id in program_ids.items():
        for promo in promotions:
            promo_id = gen_id('promo')
            promo_key = f'{prog_code}_{promo["code"]}'
            promotion_ids[promo_key] = promo_id
            db.collection('promotions').document(promo_id).set({
                'id': promo_id,
                'name': promo['name'],
                'code': promo['code'],
                'program_id': prog_id,
                'academic_year': '2025-2026',
                'created_at': now(),
                'updated_at': now(),
            })
    # UEs (3 par promotion)
    for promo_key, promo_id in promotion_ids.items():
        ue_ids[promo_key] = []
        for i in range(1, 4):
            ue_id = gen_id('ue')
            ue_ids[promo_key].append(ue_id)
            db.collection('ues').document(ue_id).set({
                'id': ue_id,
                'name': f'UE{i} {promo_key}',
                'code': f'UE{i}_{promo_key}',
                'program_id': program_ids[promo_key.split('_')[0]],
                'promotion_id': promo_id,
                'credits': 5 + i,
                'created_at': now(),
                'updated_at': now(),
            })
    # --- Création des étudiants, enseignants, admin ---
    # Création des étudiants (10 par promotion)
    for promo_key, promo_id in promotion_ids.items():
        prog_code = promo_key.split('_')[0]
        dep_id = db.collection('programs').document(program_ids[prog_code]).get().to_dict()['department_id']
        fac_id = db.collection('departments').document(dep_id).get().to_dict()['faculty_id']
        for i in range(1, 11):
            student_id = gen_id('stu')
            first_name = f'Etudiant{i}'
            last_name = f'{promo_key}'
            email = f'{first_name.lower()}.{last_name.lower()}@univ.edu'
            username = f'{first_name.lower()}{i}_{promo_key.lower()}'
            # Création dans Auth
            try:
                user = auth.create_user(email=email, password=TEST_PASSWORD, display_name=f'{first_name} {last_name}')
                auth_id = user.uid
            except Exception as e:
                print(f'Erreur création Auth étudiant {email}:', e)
                continue
            db.collection('students').document(student_id).set({
                'id': student_id,
                'first_name': first_name,
                'last_name': last_name,
                'full_name': f'{first_name} {last_name}',
                'email': email,
                'phone': f'+24389{random.randint(1000000,9999999)}',
                'gender': 'Homme' if i % 2 == 0 else 'Femme',
                'birthdate': f'200{i}-01-01',
                'program_id': program_ids[prog_code],
                'department_id': dep_id,
                'faculty_id': fac_id,
                'promotion_id': promo_id,
                'group_id': None,
                'username': username,
                'password': TEST_PASSWORD,
                'photo_url': '',
                'status': 'active',
                'created_at': now(),
                'updated_at': now(),
                'role': 'student',
                'ue_ids': ue_ids[promo_key],
                'auth_uid': auth_id,
            })
    # Création des enseignants (2 par département, chacun 2-3 UEs)
    for dep_code, dep_id in department_ids.items():
        for j in range(1, 3):
            teacher_id = gen_id('teach')
            first_name = f'Prof{j}'
            last_name = dep_code
            email = f'{first_name.lower()}.{last_name.lower()}@univ.edu'
            username = f'{first_name.lower()}{j}_{dep_code.lower()}'
            # Sélectionne 2-3 UEs aléatoires du département
            prog_ids = [pid for pcode, pid in program_ids.items() if db.collection('programs').document(pid).get().to_dict()['department_id'] == dep_id]
            promo_ids = [prid for pcode, prid in promotion_ids.items() if program_ids.get(pcode.split('_')[0]) in prog_ids]
            ue_list = []
            for prid in promo_ids:
                ue_list.extend([ue for ue in ue_ids.get([k for k,v in promotion_ids.items() if v==prid][0], [])])
            ue_sample = random.sample(ue_list, min(3, len(ue_list))) if ue_list else []
            # Création dans Auth
            try:
                user = auth.create_user(email=email, password=TEST_PASSWORD, display_name=f'{first_name} {last_name}')
                auth_id = user.uid
            except Exception as e:
                print(f'Erreur création Auth enseignant {email}:', e)
                continue
            db.collection('teachers').document(teacher_id).set({
                'id': teacher_id,
                'first_name': first_name,
                'last_name': last_name,
                'full_name': f'{first_name} {last_name}',
                'email': email,
                'phone': f'+24397{random.randint(1000000,9999999)}',
                'gender': 'Homme' if j % 2 == 0 else 'Femme',
                'birthdate': f'198{j}-01-01',
                'department_id': dep_id,
                'faculty_id': db.collection('departments').document(dep_id).get().to_dict()['faculty_id'],
                'program_id': prog_ids[0] if prog_ids else None,
                'promotion_id': promo_ids[0] if promo_ids else None,
                'group_id': None,
                'username': username,
                'password': TEST_PASSWORD,
                'photo_url': '',
                'status': 'active',
                'created_at': now(),
                'updated_at': now(),
                'role': 'teacher',
                'ue_ids': ue_sample,
                'auth_uid': auth_id,
            })
    # Création de l'admin
    try:
        user = auth.create_user(email=ADMIN_EMAIL, password=TEST_PASSWORD, display_name='Nathanael Hacker')
        auth_id = user.uid
    except Exception as e:
        print(f'Erreur création Auth admin {ADMIN_EMAIL}:', e)
        auth_id = None
    admin_id = gen_id('admin')
    db.collection('admins').document(admin_id).set({
        'id': admin_id,
        'first_name': 'Nathanael',
        'last_name': 'Hacker',
        'full_name': 'Nathanael Hacker',
        'email': ADMIN_EMAIL,
        'phone': '+243991234567',
        'gender': 'Homme',
        'birthdate': '1990-01-01',
        'username': 'nathanaelhacker',
        'password': TEST_PASSWORD,
        'photo_url': '',
        'status': 'active',
        'created_at': now(),
        'updated_at': now(),
        'role': 'admin',
        'auth_uid': auth_id,
    })
    print('Étudiants, enseignants et admin créés avec succès.')

    # --- Exemples de prénoms et noms réalistes ---
    prenoms = [
        'Nathanael', 'Patient', 'Sarah', 'Kevin', 'Aline', 'Grace', 'Emmanuel', 'Esther', 'Samuel', 'Chantal',
        'David', 'Rachel', 'Junior', 'Naomie', 'Steve', 'Josué', 'Bénédicte', 'Cédric', 'Merveille', 'Paul'
    ]
    noms = [
        'Kabongo', 'Mbuyi', 'Ilunga', 'Mutombo', 'Ngoy', 'Kalala', 'Kasongo', 'Lukusa', 'Tshibanda', 'Mukendi',
        'Mulumba', 'Katumba', 'Kabasele', 'Mpoyi', 'Kalonji', 'Mwamba', 'Muleka', 'Kanku', 'Mwanza', 'Tshisekedi'
    ]
    # --- Exemples d'UEs réalistes par filière ---
    ues_by_prog = {
        'GL': ['Algorithmique', 'Programmation', 'Bases de données', 'Systèmes d’exploitation', 'Web'],
        'RT': ['Réseaux', 'Télécoms', 'Sécurité', 'Protocoles', 'Administration'],
        'MF': ['Analyse', 'Algèbre', 'Statistiques', 'Probabilités', 'Topologie'],
        'PA': ['Mécanique', 'Optique', 'Thermodynamique', 'Électromagnétisme', 'Physique quantique'],
        'PG': ['Logique', 'Éthique', 'Métaphysique', 'Philosophie antique', 'Philosophie moderne'],
        'HM': ['Histoire ancienne', 'Histoire médiévale', 'Histoire moderne', 'Méthodologie', 'Archéologie'],
        'DC': ['Droit civil', 'Procédure civile', 'Droit des personnes', 'Droit des biens', 'Droit de la famille'],
        'DCO': ['Droit constitutionnel', 'Institutions politiques', 'Libertés publiques', 'Droit administratif', 'Droit international'],
        'MED': ['Anatomie', 'Physiologie', 'Pathologie', 'Pharmacologie', 'Médecine interne'],
        'PHAR': ['Chimie pharmaceutique', 'Pharmacognosie', 'Pharmacie clinique', 'Toxicologie', 'Biopharmacie'],
        'GE': ['Comptabilité', 'Gestion financière', 'Marketing', 'Management', 'Entrepreneuriat'],
        'EA': ['Microéconomie', 'Macroéconomie', 'Économétrie', 'Politiques économiques', 'Finances publiques'],
    }
    # --- Création des UEs (5 par promotion, noms réalistes) ---
    for promo_key, promo_id in promotion_ids.items():
        ue_ids[promo_key] = []
        prog_code = promo_key.split('_')[0]
        ue_names = ues_by_prog.get(prog_code, [f'UE{i}' for i in range(1, 6)])
        for i in range(5):
            ue_id = gen_id('ue')
            ue_ids[promo_key].append(ue_id)
            db.collection('ues').document(ue_id).set({
                'id': ue_id,
                'name': ue_names[i % len(ue_names)],
                'code': f'{ue_names[i % len(ue_names)].replace(" ", "_")}_{promo_key}',
                'program_id': program_ids[prog_code],
                'promotion_id': promo_id,
                'credits': 4 + i,
                'created_at': now(),
                'updated_at': now(),
            })
    # --- Création des étudiants (10 par promotion, noms réalistes) ---
    used_names = set()
    for promo_key, promo_id in promotion_ids.items():
        prog_code = promo_key.split('_')[0]
        dep_id = db.collection('programs').document(program_ids[prog_code]).get().to_dict()['department_id']
        fac_id = db.collection('departments').document(dep_id).get().to_dict()['faculty_id']
        for i in range(10):
            # Prénom et nom uniques
            while True:
                first_name = random.choice(prenoms)
                last_name = random.choice(noms)
                full_name = f'{first_name} {last_name}'
                if full_name not in used_names:
                    used_names.add(full_name)
                    break
            email = f'{first_name.lower()}.{last_name.lower()}.{promo_key.lower()}@univ.edu'
            username = f'{first_name.lower()}{last_name.lower()}_{promo_key.lower()}'
            # Création dans Auth
            try:
                user = auth.create_user(email=email, password=TEST_PASSWORD, display_name=full_name)
                auth_id = user.uid
            except Exception as e:
                print(f'Erreur création Auth étudiant {email}:', e)
                continue
            db.collection('students').document(gen_id('stu')).set({
                'first_name': first_name,
                'last_name': last_name,
                'full_name': full_name,
                'email': email,
                'phone': f'+24389{random.randint(1000000,9999999)}',
                'gender': 'Homme' if i % 2 == 0 else 'Femme',
                'birthdate': f'200{random.randint(0,9)}-01-01',
                'program_id': program_ids[prog_code],
                'department_id': dep_id,
                'faculty_id': fac_id,
                'promotion_id': promo_id,
                'group_id': None,
                'username': username,
                'password': TEST_PASSWORD,
                'photo_url': '',
                'status': 'active',
                'created_at': now(),
                'updated_at': now(),
                'role': 'student',
                'ue_ids': ue_ids[promo_key],
                'auth_uid': auth_id,
            })
    print('UEs et étudiants réalistes créés.')
    # --- Exemples de prénoms et noms réalistes pour enseignants ---
    prenoms_enseignants = [
        'Jean', 'Marie', 'Alain', 'Brigitte', 'Serge', 'Claire', 'Fabrice', 'Sophie', 'Pascal', 'Isabelle',
        'Laurent', 'Patricia', 'Bernard', 'Catherine', 'Olivier', 'Monique', 'Thierry', 'Nadine', 'Eric', 'Valérie'
    ]
    noms_enseignants = [
        'Mukeba', 'Kabeya', 'Lusamba', 'Kashala', 'Mabiala', 'Ngoma', 'Kitenge', 'Banza', 'Mbuyi', 'Kalonji',
        'Mwamba', 'Kabasele', 'Tshibanda', 'Ilunga', 'Mutombo', 'Kasongo', 'Katumba', 'Kanku', 'Mwanza', 'Tshisekedi'
    ]
    used_enseignant_names = set()
    # Création des enseignants (2 par département, chacun 2-3 UEs, noms réalistes)
    for dep_code, dep_id in department_ids.items():
        for j in range(2):
            # Prénom et nom uniques
            while True:
                first_name = random.choice(prenoms_enseignants)
                last_name = random.choice(noms_enseignants)
                full_name = f'{first_name} {last_name}'
                if full_name not in used_enseignant_names:
                    used_enseignant_names.add(full_name)
                    break
            email = f'{first_name.lower()}.{last_name.lower()}@univ.edu'
            username = f'{first_name.lower()}{last_name.lower()}_{dep_code.lower()}'
            # Sélectionne 2-3 UEs aléatoires du département
            prog_ids = [pid for pcode, pid in program_ids.items() if db.collection('programs').document(pid).get().to_dict()['department_id'] == dep_id]
            promo_ids = [prid for pcode, prid in promotion_ids.items() if program_ids.get(pcode.split('_')[0]) in prog_ids]
            ue_list = []
            for prid in promo_ids:
                ue_list.extend([ue for ue in ue_ids.get([k for k,v in promotion_ids.items() if v==prid][0], [])])
            ue_sample = random.sample(ue_list, min(3, len(ue_list))) if ue_list else []
            # Création dans Auth
            try:
                user = auth.create_user(email=email, password=TEST_PASSWORD, display_name=full_name)
                auth_id = user.uid
            except Exception as e:
                print(f'Erreur création Auth enseignant {email}:', e)
                continue
            db.collection('teachers').document(gen_id('teach')).set({
                'first_name': first_name,
                'last_name': last_name,
                'full_name': full_name,
                'email': email,
                'phone': f'+24397{random.randint(1000000,9999999)}',
                'gender': 'Homme' if j % 2 == 0 else 'Femme',
                'birthdate': f'197{random.randint(0,9)}-01-01',
                'department_id': dep_id,
                'faculty_id': db.collection('departments').document(dep_id).get().to_dict()['faculty_id'],
                'program_id': prog_ids[0] if prog_ids else None,
                'promotion_id': promo_ids[0] if promo_ids else None,
                'group_id': None,
                'username': username,
                'password': TEST_PASSWORD,
                'photo_url': '',
                'status': 'active',
                'created_at': now(),
                'updated_at': now(),
                'role': 'teacher',
                'ue_ids': ue_sample,
                'auth_uid': auth_id,
            })
    # Création de l'admin (infos réalistes)
    try:
        user = auth.create_user(email=ADMIN_EMAIL, password=TEST_PASSWORD, display_name='Nathanael Batera')
        auth_id = user.uid
    except Exception as e:
        print(f'Erreur création Auth admin {ADMIN_EMAIL}:', e)
        auth_id = None
    admin_id = gen_id('admin')
    db.collection('admins').document(admin_id).set({
        'id': admin_id,
        'first_name': 'Nathanael',
        'last_name': 'Batera',
        'full_name': 'Nathanael Batera',
        'email': ADMIN_EMAIL,
        'phone': '+243991234567',
        'gender': 'Homme',
        'birthdate': '1990-01-01',
        'username': 'nathanaelhacker',
        'password': TEST_PASSWORD,
        'photo_url': '',
        'status': 'active',
        'created_at': now(),
        'updated_at': now(),
        'role': 'admin',
        'auth_uid': auth_id,
    })
    print('Enseignants et admin réalistes créés.')

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
    delete_all_collections()
    create_university_structure()
    ensure_teacher_doc()
    print('Réinitialisation, création et vérification terminées.')

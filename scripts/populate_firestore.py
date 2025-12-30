import firebase_admin
from firebase_admin import credentials, firestore, auth

cred = credentials.Certificate('../app/serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

def sync_collection(collection_name, role, batch_size=500):
    last_doc = None
    while True:
        query = db.collection(collection_name).limit(batch_size)
        if last_doc:
            query = query.start_after(last_doc)
        docs = list(query.stream())
        if not docs:
            break
        for doc in docs:
            data = doc.to_dict()
            email = data.get('email')
            password = data.get('password')
            if not email or not password:
                print(f"Skip {doc.id}: missing email or password")
                continue
            # Check if user exists in Firebase Auth
            try:
                user = auth.get_user_by_email(email)
                print(f"User {email} already exists in Auth")
            except auth.UserNotFoundError:
                user = auth.create_user(email=email, password=password)
                print(f"Created user {email} in Auth")
            # Check if user exists in 'users' collection (id = user.uid)
            user_ref = db.collection('users').document(user.uid)
            user_doc = user_ref.get()
            user_data = user_doc.to_dict() if user_doc.exists else None
            # Si le doc existe mais n'est pas à jour, on le met à jour
            if not user_doc.exists or user_data is None or user_data.get('auth_uid') != user.uid or user_data.get('email') != email or user_data.get('role') != role:
                user_ref.set({
                    'email': email,
                    'role': role,
                    'auth_uid': user.uid,
                    'status': data.get('status', 'active'),
                    'full_name': data.get('full_name', ''),
                    # Ajoute d'autres champs si besoin
                })
                print(f"Updated/Added {email} to users collection")
            else:
                print(f"User {email} already up-to-date in users collection")
        last_doc = docs[-1]

sync_collection('students', 'student')
sync_collection('teachers', 'teacher')
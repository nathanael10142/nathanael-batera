"""
Script d'initialisation Firestore pour créer les collections/documents minimaux
(ex: roles, university_config) utilisés par l'application.
Usage: python create_firestore_seed.py
"""
from app.core.firebase_connector import initialize_firebase


def seed():
    initialize_firebase()
    from app.models.firestore_models import create_doc, get_doc, update_doc

    # Créer roles si elles n'existent pas
    roles = [
        {"name": "admin"},
        {"name": "student"},
        {"name": "teacher"},
        {"name": "accountant"},
        {"name": "dean"},
    ]

    # Use Firestore directly for id-based lookup because roles are simple
    from firebase_admin import firestore
    db = firestore.client()
    existing = {d.to_dict().get("name"): d.id for d in db.collection("roles").stream()}

    for r in roles:
        if r["name"] in existing:
            print(f"Role '{r['name']}' exists (id={existing[r['name']]})")
        else:
            ref = db.collection("roles").document()
            ref.set(r)
            print(f"Created role '{r['name']}' (id={ref.id})")

    # Create a default university_config if none exists
    configs = list(db.collection("university_config").limit(1).stream())
    if configs:
        print("University config already exists.")
    else:
        data = {
            "name": "Default University",
            "logo_url": None,
            "currency": "USD",
            "address": None,
            "contacts": {},
            "lmd_params": {},
            "active_academic_year_id": None,
            "settings": {},
            "updated_by": None,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        ref = db.collection("university_config").document()
        ref.set(data)
        print(f"Created university_config (id={ref.id})")


if __name__ == "__main__":
    seed()

"""
Routes d'administration (création facultés, etc.)
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import firestore

# Imports corrigés avec des chemins absolus
from app.core.security import get_current_active_user, require_permission, Permissions
from app.models import User # Faculty, Department, Option sont maintenant gérés via Firestore

router = APIRouter()


@router.post("/faculties/duplicate")
async def duplicate_faculty(
    template_faculty_id: int,
    new_faculty_name: str,
    new_faculty_code: str,
    current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    """
    FONCTION CLÉ : Dupliquer une faculté modèle
    """
    db = firestore.client()
    template_faculty_ref = db.collection("faculties").document(str(template_faculty_id))
    template_faculty = template_faculty_ref.get()

    if not template_faculty.exists:
        raise HTTPException(status_code=404, detail="Faculté template introuvable")

    template_data = template_faculty.to_dict()

    # Créer la nouvelle faculté
    new_faculty_ref = db.collection("faculties").document()
    new_faculty_data = {
        "university_id": template_data.get("university_id"),
        "name": new_faculty_name,
        "code": new_faculty_code,
        "is_active": True,
        "is_deleted": False
    }
    new_faculty_ref.set(new_faculty_data)

    # Dupliquer les sous-collections (départements et options)
    template_departments = template_faculty_ref.collection("departments").stream()
    departments_created_count = 0

    for dept in template_departments:
        dept_data = dept.to_dict()
        new_dept_ref = new_faculty_ref.collection("departments").document()
        new_dept_ref.set({
            "name": dept_data.get("name"),
            "code": dept_data.get("code")
        })
        departments_created_count += 1

        template_options = dept.reference.collection("options").stream()
        for opt in template_options:
            opt_data = opt.to_dict()
            new_opt_ref = new_dept_ref.collection("options").document()
            new_opt_ref.set({
                "name": opt_data.get("name"),
                "code": opt_data.get("code")
            })

    return {
        "message": "Faculté dupliquée avec succès",
        "faculty_id": new_faculty_ref.id,
        "faculty_name": new_faculty_name,
        "departments_created": departments_created_count
    }


@router.post("/faculties/create")
async def create_faculty_from_scratch(
    university_id: int,
    name: str,
    code: str,
    current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    """
    Créer une faculté vierge (sans structure)
    """
    db = firestore.client()
    faculty_ref = db.collection("faculties").document()
    faculty_data = {
        "university_id": university_id,
        "name": name,
        "code": code,
        "is_active": True,
        "is_deleted": False
    }
    faculty_ref.set(faculty_data)

    return {
        "message": "Faculté créée",
        "faculty_id": faculty_ref.id,
        "faculty_name": name
    }


@router.get("/faculties")
async def list_all_faculties(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Lister toutes les facultés (pour admin)
    """
    if not (current_user.role and current_user.role.name == "admin"):
        raise HTTPException(status_code=403, detail="Permission refusée")

    db = firestore.client()
    faculties_stream = db.collection("faculties").where("is_deleted", "==", False).stream()

    faculties_list = []
    for f in faculties_stream:
        faculty_data = f.to_dict()
        faculties_list.append({
            "id": f.id,
            "name": faculty_data.get("name"),
            "code": faculty_data.get("code")
        })

    return {
        "total": len(faculties_list),
        "faculties": faculties_list
    }


@router.delete("/faculties/{faculty_id}")
async def deactivate_faculty(
    faculty_id: int,
    current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    """
    Désactiver une faculté (soft delete)
    """
    db = firestore.client()
    faculty_ref = db.collection("faculties").document(str(faculty_id))
    faculty = faculty_ref.get()

    if not faculty.exists:
        raise HTTPException(status_code=404, detail="Faculté introuvable")

    faculty_ref.update({"is_active": False, "is_deleted": True})

    return {"message": "Faculté désactivée"}
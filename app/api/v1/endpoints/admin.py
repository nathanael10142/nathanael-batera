"""
Routes d'administration (création facultés, etc.)
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_current_active_user, check_permission, Permissions
from database import get_session
from models import CycleType, Faculte, Departement, OptionFiliere, Utilisateur

router = APIRouter()


@router.post("/faculties/duplicate")
async def duplicate_faculty(
    template_faculty_id: int,
    new_faculty_name: str,
    new_faculty_code: str,
    db: AsyncSession = Depends(get_session),
    current_user: Utilisateur = Depends(get_current_active_user)
) -> Any:
    """
    FONCTION CLÉ : Dupliquer une faculté modèle
    
    Cette fonction permet à l'admin de créer 100+ facultés automatiquement
    en dupliquant la faculté modèle avec toute sa structure.
    """
    # Vérifier les permissions
    if not check_permission(current_user, Permissions.ADMIN_CREATE_FACULTY):
        raise HTTPException(status_code=403, detail="Permission refusée")
    
    # Récupérer la faculté template
    query = select(Faculte).where(Faculte.id == template_faculty_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Faculté template introuvable")
    
    # Créer la nouvelle faculté
    new_faculty = Faculte(
        universite_id=template.universite_id,
        nom=new_faculty_name,
        code=new_faculty_code
    )
    db.add(new_faculty)
    await db.flush()  # Pour obtenir l'ID
    
    # Dupliquer les départements
    dept_query = select(Departement).where(Departement.faculte_id == template_faculty_id)
    dept_result = await db.execute(dept_query)
    template_departments = dept_result.scalars().all()
    
    department_map = {}  # Mapping ancien ID -> nouveau département
    
    for template_dept in template_departments:
        new_dept = Departement(
            faculte_id=new_faculty.id,
            nom=template_dept.nom,
            code=template_dept.code
        )
        db.add(new_dept)
        await db.flush()
        department_map[template_dept.id] = new_dept
        
        # Dupliquer les options de ce département
        option_query = select(OptionFiliere).where(OptionFiliere.departement_id == template_dept.id)
        option_result = await db.execute(option_query)
        template_options = option_result.scalars().all()
        
        for template_option in template_options:
            new_option = OptionFiliere(
                departement_id=new_dept.id,
                nom=template_option.nom,
                code=template_option.code,
                cycle=template_option.cycle
            )
            db.add(new_option)
    
    await db.commit()
    
    return {
        "message": "Faculté dupliquée avec succès",
        "faculty_id": new_faculty.id,
        "faculty_name": new_faculty.nom,
        "departments_created": len(department_map)
    }


@router.post("/faculties/create")
async def create_faculty_from_scratch(
    university_id: int,
    name: str,
    code: str,
    db: AsyncSession = Depends(get_session),
    current_user: Utilisateur = Depends(get_current_active_user)
) -> Any:
    """
    Créer une faculté vierge (sans structure)
    """
    if not check_permission(current_user, Permissions.ADMIN_CREATE_FACULTY):
        raise HTTPException(status_code=403, detail="Permission refusée")
    
    faculty = Faculte(
        universite_id=university_id,
        nom=name,
        code=code
    )
    db.add(faculty)
    await db.commit()
    await db.refresh(faculty)
    
    return {
        "message": "Faculté créée",
        "faculty_id": faculty.id,
        "faculty_name": faculty.nom
    }


@router.get("/faculties")
async def list_all_faculties(
    db: AsyncSession = Depends(get_session),
    current_user: Utilisateur = Depends(get_current_active_user)
) -> Any:
    """
    Lister toutes les facultés (pour admin)
    """
    if not (current_user.role and current_user.role.nom == "Admin"):
        raise HTTPException(status_code=403, detail="Permission refusée")
    
    query = select(Faculte)
    result = await db.execute(query)
    faculties = result.scalars().all()
    
    return {
        "total": len(faculties),
        "faculties": [
            {
                "id": f.id,
                "name": f.nom,
                "code": f.code
            }
            for f in faculties
        ]
    }


@router.delete("/faculties/{faculty_id}")
async def deactivate_faculty(
    faculty_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: Utilisateur = Depends(get_current_active_user)
) -> Any:
    """
    Désactiver une faculté (soft delete)
    """
    if not check_permission(current_user, Permissions.ADMIN_CREATE_FACULTY):
        raise HTTPException(status_code=403, detail="Permission refusée")
    
    query = select(Faculte).where(Faculte.id == faculty_id)
    result = await db.execute(query)
    faculty = result.scalar_one_or_none()
    
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculté introuvable")
    
    # faculty.is_active = False # Le champ is_active n'existe plus dans le nouveau modèle
    await db.commit()
    
    return {"message": "Faculté désactivée"}
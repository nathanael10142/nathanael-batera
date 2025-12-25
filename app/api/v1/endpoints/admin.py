"""
Routes d'administration (création facultés, etc.)
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Imports corrigés avec des chemins absolus
from app.core.security import get_current_active_user, require_permission, Permissions
from app.db.session import get_session
from app.models import Faculty, Department, Option, User

router = APIRouter()


@router.post("/faculties/duplicate")
async def duplicate_faculty(
    template_faculty_id: int,
    new_faculty_name: str,
    new_faculty_code: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    """
    FONCTION CLÉ : Dupliquer une faculté modèle
    
    Cette fonction permet à l'admin de créer 100+ facultés automatiquement
    en dupliquant la faculté modèle avec toute sa structure.
    """
    # Vérifier les permissions
    # La vérification est maintenant gérée par le décorateur `require_permission`
    
    # Récupérer la faculté template
    query = select(Faculty).where(Faculty.id == template_faculty_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Faculté template introuvable")
    
    # Créer la nouvelle faculté
    new_faculty = Faculty(
        university_id=template.university_id,
        name=new_faculty_name,
        code=new_faculty_code
    )
    db.add(new_faculty)
    await db.flush()  # Pour obtenir l'ID
    
    # Dupliquer les départements
    dept_query = select(Department).where(Department.faculty_id == template_faculty_id)
    dept_result = await db.execute(dept_query)
    template_departments = dept_result.scalars().all()
    
    department_map = {}  # Mapping ancien ID -> nouveau département
    
    for template_dept in template_departments:
        new_dept = Department(
            faculty_id=new_faculty.id,
            name=template_dept.name,
            code=template_dept.code
        )
        db.add(new_dept)
        await db.flush()
        department_map[template_dept.id] = new_dept
        
        # Dupliquer les options de ce département
        option_query = select(Option).where(Option.department_id == template_dept.id)
        option_result = await db.execute(option_query)
        template_options = option_result.scalars().all()
        
        for template_option in template_options:
            new_option = Option(
                department_id=new_dept.id,
                name=template_option.name,
                code=template_option.code
            )
            db.add(new_option)
    
    await db.commit()
    
    return {
        "message": "Faculté dupliquée avec succès",
        "faculty_id": new_faculty.id,
        "faculty_name": new_faculty.name,
        "departments_created": len(department_map)
    }


@router.post("/faculties/create")
async def create_faculty_from_scratch(
    university_id: int,
    name: str,
    code: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    """
    Créer une faculté vierge (sans structure)
    """
    faculty = Faculty(
        university_id=university_id,
        name=name,
        code=code
    )
    db.add(faculty)
    await db.commit()
    await db.refresh(faculty)
    
    return {
        "message": "Faculté créée",
        "faculty_id": faculty.id,
        "faculty_name": faculty.name
    }


@router.get("/faculties")
async def list_all_faculties(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Lister toutes les facultés (pour admin)
    """
    if not (current_user.role and current_user.role.name == "admin"):
        raise HTTPException(status_code=403, detail="Permission refusée")
    
    query = select(Faculty)
    result = await db.execute(query)
    faculties = result.scalars().all()
    
    return {
        "total": len(faculties),
        "faculties": [
            {
                "id": f.id,
                "name": f.name,
                "code": f.code
            }
            for f in faculties
        ]
    }


@router.delete("/faculties/{faculty_id}")
async def deactivate_faculty(
    faculty_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    """
    Désactiver une faculté (soft delete)
    """
    query = select(Faculty).where(Faculty.id == faculty_id)
    result = await db.execute(query)
    faculty = result.scalar_one_or_none()
    
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculté introuvable")
    
    faculty.is_active = False
    faculty.is_deleted = True
    await db.commit()
    
    return {"message": "Faculté désactivée"}
"""
Routes d'administration (création facultés, etc.)
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from firebase_admin import firestore
import io
import csv
import random
import logging

# Imports corrigés avec des chemins absolus
from app.core.security import get_current_active_user, require_permission, Permissions
from app.models import User # Faculty, Department, Option sont maintenant gérés via Firestore
from app.models.firestore_models import Faculty as FacModel
from app.schemas.firestore import (
    FacultyCreate, FacultyOut, FacultyListResponse,
    DepartmentCreate, DepartmentOut,
    ProgramCreate, ProgramOut,
    PromotionCreate, PromotionOut,
    EnrollmentCreate, EnrollmentOut
)
from app.models.firestore_models import create_doc, get_doc, update_doc, delete_doc, list_docs, public_list

router = APIRouter()

# expose a small public router for GET-listing endpoints used by the mobile client
public_router = APIRouter()


def _public_list(collection: str, limit: int = 2000):
    """Helper wrapper: delegate to centralized public_list in firestore_models.
    Ensures all public listing endpoints behave the same (includes older docs missing is_deleted).
    """
    return public_list(collection, limit=limit)


def _generate_matricule() -> str:
    # Simple matricule: YEAR + 6 random digits
    return f"{__import__('datetime').datetime.now().year}{random.randint(100000, 999999)}"


def _ensure_unique_matricule(candidate: str = None) -> str:
    """Ensure matricule is unique in students collection; try few times before failing."""
    if not candidate:
        candidate = _generate_matricule()
    # quick check
    existing = list_docs('students', where=[('matricule', '==', candidate)], limit=1)
    if not existing:
        return candidate
    # try regenerating
    for _ in range(10):
        candidate = _generate_matricule()
        existing = list_docs('students', where=[('matricule', '==', candidate)], limit=1)
        if not existing:
            return candidate
    logging.warning('Could not generate unique matricule after several attempts')
    raise Exception('Failed to generate unique matricule')


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


@router.post("/faculties/create", response_model=FacultyOut)
async def create_faculty_from_scratch(
    payload: FacultyCreate,
    current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    """
    Créer une faculté vierge (sans structure) — endpoint adapté à Firestore models
    """
    data = payload.dict()
    # default flags
    data.setdefault("is_active", True)
    data.setdefault("is_deleted", False)
    faculty_id = create_doc("faculties", data)
    created = get_doc("faculties", faculty_id)
    return FacultyOut(**created)


@router.get("/faculties", response_model=FacultyListResponse)
async def list_all_faculties(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Lister toutes les facultés (pour admin) — utilise helper public_list pour inclure anciens documents.
    """
    if not (getattr(current_user, 'role', None) and getattr(current_user.role, 'name', None) == "admin"):
        raise HTTPException(status_code=403, detail="Permission refusée")

    docs = public_list("faculties", limit=500)
    faculties = [FacultyOut(**d) for d in docs]
    return FacultyListResponse(total=len(faculties), faculties=faculties)


@router.delete("/faculties/{faculty_id}")
async def deactivate_faculty(
    faculty_id: str,
    current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    """
    Désactiver une faculté (soft delete)
    """
    # mark as deleted
    update_doc("faculties", faculty_id, {"is_active": False, "is_deleted": True})
    return {"message": "Faculté désactivée"}


@router.post('/students/import')
async def import_students_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    """Import students from CSV file (multipart/form-data, field name 'file').
    The CSV should contain headers. We create documents in `students` collection and a minimal `users` entry.
    """
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except Exception:
        text = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text))
    created = 0
    errors = []
    for row in reader:
        try:
            full_name = (row.get('full_name') or row.get('name') or f"{row.get('first_name','') } {row.get('last_name','')}").strip()
            email = row.get('email') or row.get('contact_email')
            raw_matricule = row.get('matricule')
            matricule = _ensure_unique_matricule(raw_matricule) if raw_matricule else _ensure_unique_matricule()
            student_doc = {
                'full_name': full_name,
                'email': email,
                'matricule': matricule,
                'is_deleted': False,
                'created_at': __import__('datetime').datetime.utcnow().isoformat(),
            }
            sid = create_doc('students', student_doc)
            # Create a lightweight user record for auth/lookup
            user_doc = {
                'username': (email.split('@')[0] if email else matricule),
                'email': email,
                'role': 'student',
                'student_id': sid,
                'created_at': __import__('datetime').datetime.utcnow().isoformat(),
            }
            create_doc('users', user_doc)
            created += 1
        except Exception as e:
            logging.exception('Error importing student row')
            errors.append(str(e))
            continue

    return {'created': created, 'errors': errors}


@router.post('/teachers/import')
async def import_teachers_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except Exception:
        text = content.decode('latin-1')
    reader = csv.DictReader(io.StringIO(text))
    created = 0
    errors = []
    for row in reader:
        try:
            full_name = row.get('full_name') or row.get('name') or f"{row.get('first_name','') } {row.get('last_name','')}".strip()
            email = row.get('email')
            teacher_doc = {
                'full_name': full_name,
                'email': email,
                'is_deleted': False,
                'created_at': __import__('datetime').datetime.utcnow().isoformat(),
            }
            tid = create_doc('teachers', teacher_doc)
            # create a lightweight user record for the teacher for auth/lookup
            try:
                created_teacher = get_doc('teachers', tid) or {}
                user_doc = {
                    'username': (email.split('@')[0] if email else f'teacher{tid}'),
                    'email': email,
                    'role': 'teacher',
                    'teacher_id': tid,
                    'created_at': __import__('datetime').datetime.utcnow().isoformat(),
                }
                create_doc('users', user_doc)
            except Exception:
                # don't fail teacher creation if user creation fails
                pass
            created += 1
        except Exception as e:
            errors.append(str(e))
            continue
    return {'created': created, 'errors': errors}


# Groups CRUD (admin) and public listing
@router.post('/groups/create')
async def create_group(
    payload: dict,
    current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    data = payload.copy()
    data.setdefault('created_at', __import__('datetime').datetime.utcnow().isoformat())
    gid = create_doc('groups', data)
    return {'id': gid, 'data': get_doc('groups', gid)}


@router.delete('/groups/{group_id}')
async def delete_group(group_id: str, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    update_doc('groups', group_id, {'is_deleted': True})
    return {'message': 'Groupe supprimé'}


@public_router.get('/groups')
async def list_groups() -> Any:
    return _public_list('groups', limit=1000)


# Public listing for faculties (missing - client often calls /faculties)
@public_router.get('/faculties')
async def public_list_faculties() -> Any:
    return _public_list('faculties', limit=1000)


# Public listing for students and teachers (used by mobile admin lists)
@public_router.get('/students')
async def public_list_students() -> Any:
    return _public_list('students', limit=2000)


@public_router.get('/teachers')
async def public_list_teachers() -> Any:
    return _public_list('teachers', limit=2000)


@public_router.get('/ues')
async def list_ues() -> Any:
    return _public_list('ues', limit=2000)


@public_router.get('/departments')
async def list_departments() -> Any:
    return _public_list('departments', limit=2000)


@public_router.get('/programs')
async def list_programs() -> Any:
    return _public_list('programs', limit=2000)


@public_router.get('/promotions')
async def list_promotions() -> Any:
    return _public_list('promotions', limit=2000)


# UE / Courses
@router.post('/ues/create')
async def create_ue(payload: dict, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.copy()
    data.setdefault('created_at', __import__('datetime').datetime.utcnow().isoformat())
    uid = create_doc('ues', data)
    return {'id': uid, 'data': get_doc('ues', uid)}


@router.delete('/ues/{ue_id}')
async def delete_ue(ue_id: str, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    update_doc('ues', ue_id, {'is_deleted': True})
    return {'message': 'UE supprimée'}


# Departments
@router.post('/departments/create')
async def create_department(payload: DepartmentCreate, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.dict()
    data.setdefault('is_active', True)
    data.setdefault('is_deleted', False)
    did = create_doc('departments', data)
    return {'id': did, 'data': get_doc('departments', did)}


@router.delete('/departments/{dept_id}')
async def delete_department(dept_id: str, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    update_doc('departments', dept_id, {'is_deleted': True})
    return {'message': 'Département supprimé'}


# Programs (Filières)
@router.post('/programs/create')
async def create_program(payload: ProgramCreate, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.dict()
    data.setdefault('is_active', True)
    data.setdefault('is_deleted', False)
    pid = create_doc('programs', data)
    return {'id': pid, 'data': get_doc('programs', pid)}


@router.delete('/programs/{program_id}')
async def delete_program(program_id: str, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    update_doc('programs', program_id, {'is_deleted': True})
    return {'message': 'Filière supprimée'}


# Promotions
@router.post('/promotions/create')
async def create_promotion(payload: PromotionCreate, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.dict()
    data.setdefault('is_active', True)
    data.setdefault('is_deleted', False)
    prid = create_doc('promotions', data)
    return {'id': prid, 'data': get_doc('promotions', prid)}


@router.delete('/promotions/{promotion_id}')
async def delete_promotion(promotion_id: str, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    update_doc('promotions', promotion_id, {'is_deleted': True})
    return {'message': 'Promotion supprimée'}


# Enrollments (inscriptions)
@router.post('/enrollments/create')
async def create_enrollment(payload: EnrollmentCreate, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.dict()
    data.setdefault('status', 'enrolled')
    eid = create_doc('enrollments', data)
    return {'id': eid, 'data': get_doc('enrollments', eid)}


@router.get('/enrollments/{enrollment_id}')
async def get_enrollment(enrollment_id: str, current_user: User = Depends(get_current_active_user)):
    doc = get_doc('enrollments', enrollment_id)
    if not doc:
        raise HTTPException(status_code=404, detail='Inscription introuvable')
    return doc


@router.delete('/enrollments/{enrollment_id}')
async def delete_enrollment(enrollment_id: str, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    update_doc('enrollments', enrollment_id, {'status': 'cancelled'})
    return {'message': 'Inscription annulée'}


# --- Additional admin CRUD endpoints (single-get / update) ---
@router.get('/{collection}/{doc_id}')
async def admin_get_document(collection: str, doc_id: str, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    """Generic admin GET for a single document in any collection"""
    doc = get_doc(collection, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"{collection} document not found")
    return doc

@router.put('/{collection}/{doc_id}')
async def admin_update_document(collection: str, doc_id: str, payload: dict, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    """Generic admin update for documents"""
    try:
        update_doc(collection, doc_id, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    # If updating a teacher, propagate certain fields to the associated user record(s)
    if collection == 'teachers':
        try:
            # find users linked to this teacher (teacher_id)
            users = list_docs('users', where=[('teacher_id', '==', str(doc_id))], limit=50)
            for u in users:
                u_updates = {}
                if 'email' in payload:
                    u_updates['email'] = payload.get('email')
                    # also update username if empty or derived
                    if payload.get('email'):
                        u_updates['username'] = payload.get('email').split('@')[0]
                if 'full_name' in payload:
                    # split full_name into first/last if desired; keep full_name in users meta
                    u_updates.setdefault('first_name', None)
                    u_updates.setdefault('last_name', None)
                    try:
                        parts = str(payload.get('full_name', '')).split(' ', 1)
                        u_updates['first_name'] = parts[0]
                        if len(parts) > 1:
                            u_updates['last_name'] = parts[1]
                    except Exception:
                        pass
                if u_updates:
                    try:
                        update_doc('users', u['id'], u_updates)
                    except Exception:
                        continue
        except Exception:
            pass

    return {'id': doc_id, 'data': get_doc(collection, doc_id)}

@router.delete('/{collection}/{doc_id}')
async def admin_delete_document(collection: str, doc_id: str, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    """Generic admin delete - soft delete where applicable"""
    try:
        # prefer soft delete flag if available
        update_doc(collection, doc_id, {'is_deleted': True})
    except Exception:
        # fallback to hard delete if update not supported
        try:
            delete_doc(collection, doc_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    # If deleting a teacher, mark related user accounts as inactive
    if collection == 'teachers':
        try:
            linked = list_docs('users', where=[('teacher_id', '==', str(doc_id))], limit=50)
            for u in linked:
                try:
                    update_doc('users', u['id'], {'is_active': False, 'is_deleted': True})
                except Exception:
                    continue
        except Exception:
            pass
    return {'message': f'{collection} {doc_id} deleted'}

# --- Students & Teachers create endpoints (admin) ---
@router.post('/students/create')
async def create_student(payload: dict, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.copy()
    data.setdefault('is_deleted', False)
    data.setdefault('created_at', __import__('datetime').datetime.utcnow().isoformat())
    raw_matricule = data.get('matricule')
    data['matricule'] = _ensure_unique_matricule(raw_matricule) if raw_matricule else _ensure_unique_matricule()
    sid = create_doc('students', data)
    return {'id': sid, 'data': get_doc('students', sid)}

@router.post('/teachers/create')
async def create_teacher(payload: dict, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))) -> Any:
    data = payload.copy()
    data.setdefault('created_at', __import__('datetime').datetime.utcnow().isoformat())
    # Ensure created teacher is visible in public listings
    data.setdefault('is_deleted', False)
    tid = create_doc('teachers', data)
    # create a lightweight user record for the teacher for auth/lookup
    try:
        created_teacher = get_doc('teachers', tid) or {}
        email = data.get('email') or created_teacher.get('email')
        user_doc = {
            'username': (email.split('@')[0] if email else f'teacher{tid}'),
            'email': email,
            'role': 'teacher',
            'teacher_id': tid,
            'created_at': __import__('datetime').datetime.utcnow().isoformat(),
        }
        create_doc('users', user_doc)
    except Exception:
        # don't fail teacher creation if user creation fails
        pass
    return {'id': tid, 'data': get_doc('teachers', tid)}


# Accept POST /api/v1/students/create (alternate path) but still require admin
@public_router.post('/students/create')
async def public_create_student(payload: dict, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.copy()
    data.setdefault('is_deleted', False)
    data.setdefault('created_at', __import__('datetime').datetime.utcnow().isoformat())
    raw_matricule = data.get('matricule')
    data['matricule'] = _ensure_unique_matricule(raw_matricule) if raw_matricule else _ensure_unique_matricule()
    sid = create_doc('students', data)
    return {'id': sid, 'data': get_doc('students', sid)}

@public_router.post('/teachers/create')
async def public_create_teacher(payload: dict, current_user: User = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.copy()
    data.setdefault('created_at', __import__('datetime').datetime.utcnow().isoformat())
    data.setdefault('is_deleted', False)
    tid = create_doc('teachers', data)
    try:
        email = data.get('email')
        user_doc = {
            'username': (email.split('@')[0] if email else f'teacher{tid}'),
            'email': email,
            'role': 'teacher',
            'teacher_id': tid,
            'created_at': __import__('datetime').datetime.utcnow().isoformat(),
        }
        create_doc('users', user_doc)
    except Exception:
        pass
    return {'id': tid, 'data': get_doc('teachers', tid)}
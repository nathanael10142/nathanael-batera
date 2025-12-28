"""
Routes d'administration (création facultés, etc.)
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from firebase_admin import firestore, auth as firebase_auth
import io
import csv
import random
import logging
import secrets
import string
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta

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
from app.core.config import settings

router = APIRouter()

# expose a small public router for GET-listing endpoints used by the mobile client
public_router = APIRouter()


def _public_list(collection: str, limit: int = 2000):
    """Helper wrapper: delegate to centralized public_list in firestore_models.
    Ensures all public listing endpoints behave the same (includes older docs missing is_deleted).
    """
    return public_list(collection, limit=limit)


# New helper: validate related document existence
def _ensure_exists(collection: str, doc_id: Any, required: bool = True):
    """Ensure a referenced document exists in Firestore.
    If required is True and doc_id is falsy, raises HTTPException(400).
    If the referenced document does not exist, raises HTTPException(400).
    Returns True if exists, False if not required and not provided.
    """
    if doc_id is None or (isinstance(doc_id, str) and doc_id.strip() == ""):
        if required:
            raise HTTPException(status_code=400, detail=f"{collection}_id is required")
        return False
    try:
        found = get_doc(collection, str(doc_id))
    except Exception as e:
        logging.exception("Error while checking existence of %s %s", collection, doc_id)
        raise HTTPException(status_code=400, detail=f"Error validating {collection} relation: {e}")
    if not found:
        raise HTTPException(status_code=400, detail=f"{collection} '{doc_id}' not found")
    return True


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


def generate_random_password(length: int = 12) -> str:
    """Generate a reasonably strong random password for admin-created users when none is provided."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@router.post("/faculties/duplicate")
async def duplicate_faculty(
    template_faculty_id: int,
    new_faculty_name: str,
    new_faculty_code: str,
    current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
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
    current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    """
    Créer une faculté vierge (sans structure) — endpoint adapté à Firestore models
    """
    data = payload.dict()
    # default flags
    data.setdefault("is_active", True)
    data.setdefault("is_deleted", False)
    try:
        faculty_id = create_doc("faculties", data)
    except Exception as e:
        logging.exception("Failed to create faculty via create_doc")
        raise HTTPException(status_code=500, detail=f"Failed to create faculty: {e}")

    created = get_doc("faculties", faculty_id)
    if not created:
        logging.error("create_faculty_from_scratch: create_doc returned id=%s but get_doc returned None", faculty_id)
        raise HTTPException(status_code=500, detail="Faculty creation reported success but document not found. Check Firebase initialization/credentials.")
    return FacultyOut(**created)


@router.get("/faculties", response_model=FacultyListResponse)
async def list_all_faculties(
    current_user: Any = Depends(get_current_active_user)
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
    current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
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
    current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
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
    current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
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
    current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))
) -> Any:
    data = payload.copy()
    # groups should be linked to a promotion (and optionally to a program)
    if not data.get('promotion_id'):
        raise HTTPException(status_code=400, detail='promotion_id is required for groups')
    _ensure_exists('promotions', data.get('promotion_id'))
    if data.get('program_id'):
        _ensure_exists('programs', data.get('program_id'))
    data.setdefault('created_at', __import__('datetime').datetime.utcnow().isoformat())
    try:
        gid = create_doc('groups', data)
    except Exception as e:
        logging.exception('Failed to create group')
        raise HTTPException(status_code=500, detail=f'Failed to create group: {e}')
    created = get_doc('groups', gid)
    if not created:
        logging.error("create_group: create_doc returned id=%s but get_doc returned None", gid)
        raise HTTPException(status_code=500, detail='Group creation reported success but document not found. Check Firebase credentials.')
    return {'id': gid, 'data': created}


@router.delete('/groups/{group_id}')
async def delete_group(group_id: str, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
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
async def create_ue(payload: dict, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.copy() if isinstance(payload, dict) else payload.dict()
    # UE must be attached to a program
    if not data.get('program_id'):
        raise HTTPException(status_code=400, detail='program_id is required for UEs')
    _ensure_exists('programs', data.get('program_id'))
    data.setdefault('created_at', __import__('datetime').datetime.utcnow().isoformat())
    try:
        uid = create_doc('ues', data)
    except Exception as e:
        logging.exception('Failed to create UE')
        raise HTTPException(status_code=500, detail=f'Failed to create UE: {e}')
    created = get_doc('ues', uid)
    if not created:
        logging.error("create_ue: create_doc returned id=%s but get_doc returned None", uid)
        raise HTTPException(status_code=500, detail='UE creation reported success but document not found. Check Firebase credentials.')
    return {'id': uid, 'data': created}


@router.delete('/ues/{ue_id}')
async def delete_ue(ue_id: str, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    update_doc('ues', ue_id, {'is_deleted': True})
    return {'message': 'UE supprimée'}


# Departments
@router.post('/departments/create')
async def create_department(payload: DepartmentCreate, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.dict()
    # department must belong to a faculty
    if not data.get('faculty_id'):
        raise HTTPException(status_code=400, detail='faculty_id is required for departments')
    _ensure_exists('faculties', data.get('faculty_id'))
    data.setdefault('is_active', True)
    data.setdefault('is_deleted', False)
    try:
        did = create_doc('departments', data)
    except Exception as e:
        logging.exception('Failed to create department')
        raise HTTPException(status_code=500, detail=f'Failed to create department: {e}')
    created = get_doc('departments', did)
    if not created:
        logging.error("create_department: create_doc returned id=%s but get_doc returned None", did)
        raise HTTPException(status_code=500, detail='Department creation reported success but document not found. Check Firebase credentials.')
    return {'id': did, 'data': created}


@router.delete('/departments/{dept_id}')
async def delete_department(dept_id: str, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    update_doc('departments', dept_id, {'is_deleted': True})
    return {'message': 'Département supprimé'}


# Programs (Filières)
@router.post('/programs/create')
async def create_program(payload: ProgramCreate, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.dict()
    # program should be linked to a faculty; department is optional but if provided must exist
    if not data.get('faculty_id'):
        raise HTTPException(status_code=400, detail='faculty_id is required for programs')
    _ensure_exists('faculties', data.get('faculty_id'))
    if data.get('department_id'):
        _ensure_exists('departments', data.get('department_id'))
    data.setdefault('is_active', True)
    data.setdefault('is_deleted', False)
    try:
        pid = create_doc('programs', data)
    except Exception as e:
        logging.exception('Failed to create program')
        raise HTTPException(status_code=500, detail=f'Failed to create program: {e}')
    created = get_doc('programs', pid)
    if not created:
        logging.error("create_program: create_doc returned id=%s but get_doc returned None", pid)
        raise HTTPException(status_code=500, detail='Program creation reported success but document not found. Check Firebase credentials.')
    return {'id': pid, 'data': created}


@router.delete('/programs/{program_id}')
async def delete_program(program_id: str, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    update_doc('programs', program_id, {'is_deleted': True})
    return {'message': 'Filière supprimée'}


# Promotions
@router.post('/promotions/create')
async def create_promotion(payload: PromotionCreate, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.dict()
    # promotion must belong to a program
    if not data.get('program_id'):
        raise HTTPException(status_code=400, detail='program_id is required for promotions')
    _ensure_exists('programs', data.get('program_id'))
    data.setdefault('is_active', True)
    data.setdefault('is_deleted', False)
    try:
        prid = create_doc('promotions', data)
    except Exception as e:
        logging.exception('Failed to create promotion')
        raise HTTPException(status_code=500, detail=f'Failed to create promotion: {e}')
    created = get_doc('promotions', prid)
    if not created:
        logging.error("create_promotion: create_doc returned id=%s but get_doc returned None", prid)
        raise HTTPException(status_code=500, detail='Promotion creation reported success but document not found. Check Firebase credentials.')
    return {'id': prid, 'data': created}


# Enrollments (inscriptions)
@router.post('/enrollments/create')
async def create_enrollment(payload: EnrollmentCreate, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.dict()
    data.setdefault('status', 'enrolled')
    try:
        eid = create_doc('enrollments', data)
    except Exception as e:
        logging.exception('Failed to create enrollment')
        raise HTTPException(status_code=500, detail=f'Failed to create enrollment: {e}')
    created = get_doc('enrollments', eid)
    if not created:
        logging.error("create_enrollment: create_doc returned id=%s but get_doc returned None", eid)
        raise HTTPException(status_code=500, detail='Enrollment creation reported success but document not found. Check Firebase credentials.')
    return {'id': eid, 'data': created}


# --- Additional admin CRUD endpoints (single-get / update) ---
@router.get('/dashboard/summary')
async def dashboard_summary():
    """Return dashboard summary counts and recent 7-day series.
    This endpoint is defensive: if any error occurs (including a missing "dashboard" document),
    it will fall back to computing counts by listing collections and always return HTTP 200 with
    a consistent payload to the client.
    """
    project = getattr(settings, 'PROJECT_ID', None)
    collections = ['faculties', 'programs', 'promotions', 'ues', 'departments', 'groups', 'students', 'teachers', 'users']
    counts: dict = {}
    recent: dict = {}
    now = datetime.utcnow()
    start = now - timedelta(days=6)

    try:
        # Primary attempt: compute counts and recent series from existing documents
        for col in collections:
            try:
                docs = list_docs(col)
            except Exception as e:
                logging.exception('Error listing collection %s: %s', col, e)
                counts[col] = 0
                recent[col] = [0] * 7
                continue

            # docs may be list of dicts
            counts[col] = len(docs) if isinstance(docs, list) else 0

            # build 7-day series based on created_at if present
            series = [0] * 7
            if isinstance(docs, list):
                for d in docs:
                    created = None
                    if isinstance(d, dict):
                        created_at = d.get('created_at') or d.get('createdAt')
                        if created_at:
                            try:
                                created = datetime.fromisoformat(created_at)
                            except Exception:
                                created = None
                    if not created:
                        continue
                    if created < start or created > now:
                        continue
                    idx = (created.date() - start.date()).days
                    if 0 <= idx < 7:
                        series[idx] += 1
            recent[col] = series

    except Exception as e:
        # If something unexpected happens, attempt a best-effort fallback using list_docs per collection
        logging.exception('Unexpected error building dashboard summary: %s', e)
        for col in collections:
            try:
                docs = list_docs(col)
                counts[col] = len(docs) if isinstance(docs, list) else 0
                recent[col] = [0] * 7
            except Exception:
                counts[col] = 0
                recent[col] = [0] * 7

    # Always return a consistent successful payload (frontend expects HTTP 200)
    return {'ok': True, 'project': project, 'counts': counts, 'recent': recent}


@router.get('/{collection}/{doc_id}')
async def admin_get_document(collection: str, doc_id: str, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    """Generic admin GET for a single document in any collection"""
    doc = get_doc(collection, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"{collection} document not found")
    return doc

@router.put('/{collection}/{doc_id}')
async def admin_update_document(collection: str, doc_id: str, payload: dict, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
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
async def admin_delete_document(collection: str, doc_id: str, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
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
async def create_student(payload: dict, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    data = payload.copy()
    # Ensure email is present as we will create a Firebase Auth user
    email = data.get('email')
    if not email:
        raise HTTPException(status_code=400, detail='email is required to create a student account')

    username = data.get('username') or email
    password = data.get('password') or generate_random_password()

    # Create Firebase Auth user first to avoid orphaned student documents
    try:
        user_record = firebase_auth.create_user(email=email, password=password, display_name=username)
        uid = user_record.uid
    except Exception as e:
        logging.exception('Failed to create Firebase Auth user for student %s', email)
        # Surface a friendly error for duplicate emails
        if hasattr(e, 'code') and 'EMAIL_EXISTS' in str(e):
            raise HTTPException(status_code=400, detail=f'Email {email} already exists')
        raise HTTPException(status_code=500, detail=f'Failed to create auth user: {e}')

    # prepare student document
    data.setdefault('is_deleted', False)
    data.setdefault('created_at', __import__('datetime').datetime.utcnow().isoformat())
    raw_matricule = data.get('matricule')
    data['matricule'] = _ensure_unique_matricule(raw_matricule) if raw_matricule else _ensure_unique_matricule()

    # validate optional relations if present
    if data.get('promotion_id'):
        _ensure_exists('promotions', data.get('promotion_id'), required=True)
    if data.get('group_id'):
        _ensure_exists('groups', data.get('group_id'), required=True)
    if data.get('program_id'):
        _ensure_exists('programs', data.get('program_id'), required=True)

    try:
        sid = create_doc('students', data)
    except Exception as e:
        logging.exception('Failed to create student document; rolling back auth user')
        try:
            firebase_auth.delete_user(uid)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f'Failed to create student: {e}')

    # Create corresponding user profile document with Firebase UID as document id
    try:
        db = firestore.client()
        user_doc = {
            'firebase_uid': uid,
            'email': email,
            'username': username,
            'role': 'student',
            'student_id': sid,
            'created_at': __import__('datetime').datetime.utcnow().isoformat(),
            'is_active': True,
        }
        db.collection('users').document(uid).set(user_doc)
    except Exception as e:
        logging.exception('Failed to create user profile for student; rolling back student and auth')
        try:
            update_doc('students', sid, {'is_deleted': True})
        except Exception:
            pass
        try:
            firebase_auth.delete_user(uid)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f'Failed to create user profile: {e}')

    # Return student id and created auth uid. Include autogenerated password only when the admin didn't provide one.
    response = {'id': sid, 'user_uid': uid}
    if 'password' not in payload:
        response['password'] = password
    return response


@router.post('/teachers/create')
async def create_teacher(payload: dict, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))) -> Any:
    data = payload.copy()
    email = data.get('email')
    username = data.get('username') or (email if email else None) or data.get('full_name')
    password = data.get('password') or generate_random_password()

    # If we have an email, create Firebase Auth user first
    uid = None
    if email:
        try:
            user_record = firebase_auth.create_user(email=email, password=password, display_name=username)
            uid = user_record.uid
        except Exception as e:
            logging.exception('Failed to create Firebase Auth user for teacher %s', email)
            if hasattr(e, 'code') and 'EMAIL_EXISTS' in str(e):
                raise HTTPException(status_code=400, detail=f'Email {email} already exists')
            raise HTTPException(status_code=500, detail=f'Failed to create auth user: {e}')

    data.setdefault('created_at', __import__('datetime').datetime.utcnow().isoformat())
    data.setdefault('is_deleted', False)
    # validate relations if present
    if data.get('department_id'):
        _ensure_exists('departments', data.get('department_id'))
    ues = data.get('ues') or data.get('ue_ids')
    if isinstance(ues, (list, tuple)):
        for u in ues:
            _ensure_exists('ues', u)

    try:
        tid = create_doc('teachers', data)
    except Exception as e:
        logging.exception('Failed to create teacher')
        # rollback auth user if created
        if uid:
            try:
                firebase_auth.delete_user(uid)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f'Failed to create teacher: {e}')

    created = get_doc('teachers', tid)
    if not created:
        logging.error("create_teacher: create_doc returned id=%s but get_doc returned None", tid)
        # rollback
        try:
            update_doc('teachers', tid, {'is_deleted': True})
        except Exception:
            pass
        if uid:
            try:
                firebase_auth.delete_user(uid)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail='Teacher creation reported success but document not found. Check Firebase credentials.')

    # create a lightweight user record for the teacher for auth/lookup
    try:
        db = firestore.client()
        user_doc = {
            'firebase_uid': uid or None,
            'username': username or (email.split('@')[0] if email else f'teacher{tid}'),
            'email': email,
            'role': 'teacher',
            'teacher_id': tid,
            'created_at': __import__('datetime').datetime.utcnow().isoformat(),
            'is_active': True,
        }
        # prefer to write document with firebase uid if available
        if uid:
            db.collection('users').document(uid).set(user_doc)
        else:
            # create auto-id doc
            create_doc('users', user_doc)
    except Exception:
        # don't fail teacher creation if user creation fails, but log
        logging.exception('Failed to create linked user for teacher')

    response = {'id': tid, 'data': created}
    # include generated password only if not explicitly provided
    if 'password' not in payload:
        response['password'] = password
    return response


# Accept POST /api/v1/students/create (alternate path) but still require admin
@public_router.post('/students/create')
async def public_create_student(payload: dict, current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    # Mirror the admin create behaviour: create Firebase Auth user and profile too
    data = payload.copy()
    email = data.get('email')
    if not email:
        raise HTTPException(status_code=400, detail='email is required to create a student account')
    username = data.get('username') or email
    password = data.get('password') or generate_random_password()

    try:
        user_record = firebase_auth.create_user(email=email, password=password, display_name=username)
        uid = user_record.uid
    except Exception as e:
        logging.exception('Failed to create Firebase Auth user for public student create %s', email)
        if hasattr(e, 'code') and 'EMAIL_EXISTS' in str(e):
            raise HTTPException(status_code=400, detail=f'Email {email} already exists')
        raise HTTPException(status_code=500, detail=f'Failed to create auth user: {e}')

    data.setdefault('is_deleted', False)
    data.setdefault('created_at', __import__('datetime').datetime.utcnow().isoformat())
    raw_matricule = data.get('matricule')
    data['matricule'] = _ensure_unique_matricule(raw_matricule) if raw_matricule else _ensure_unique_matricule()

    if data.get('promotion_id'):
        _ensure_exists('promotions', data.get('promotion_id'))
    if data.get('group_id'):
        _ensure_exists('groups', data.get('group_id'))
    if data.get('program_id'):
        _ensure_exists('programs', data.get('program_id'))

    try:
        sid = create_doc('students', data)
    except Exception as e:
        logging.exception('Failed to create student (public); rolling back auth user')
        try:
            firebase_auth.delete_user(uid)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f'Failed to create student: {e}')

    try:
        db = firestore.client()
        user_doc = {
            'firebase_uid': uid,
            'email': email,
            'username': username,
            'role': 'student',
            'student_id': sid,
            'created_at': __import__('datetime').datetime.utcnow().isoformat(),
            'is_active': True,
        }
        db.collection('users').document(uid).set(user_doc)
    except Exception as e:
        logging.exception('Failed to create user profile for student (public); rolling back')
        try:
            update_doc('students', sid, {'is_deleted': True})
        except Exception:
            pass
        try:
            firebase_auth.delete_user(uid)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f'Failed to create user profile: {e}')

    response = {'id': sid, 'user_uid': uid}
    if 'password' not in payload:
        response['password'] = password
    return response


@public_router.get('/debug/firestore')
async def debug_firestore_info(current_user: Any = Depends(require_permission(Permissions.ADMIN_CREATE_FACULTY))):
    """Debug helper: return Firestore project id and counts for key collections.
    Protected to admins to avoid exposing project details publicly.
    """
    try:
        db = firestore.client()
        project = getattr(db, 'project', None)
    except Exception as e:
        logging.exception('Failed to obtain Firestore client')
        return {'ok': False, 'error': str(e)}

    collections = ['faculties', 'programs', 'promotions', 'ues', 'groups', 'students', 'teachers', 'departments', 'users']
    counts = {}
    for c in collections:
        try:
            docs = list_docs(c, limit=5000)
            counts[c] = len(docs)
        except Exception as e:
            counts[c] = f'error: {e}'
    return {'ok': True, 'project': project, 'counts': counts}

@router.get('/students/{student_id}/dashboard')
async def student_dashboard(student_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    """Return a compact dashboard for a single student usable by the mobile client.
    Accessible to the student themself or to admin users.
    The response is defensive and always returns an object with keys used by the mobile UI.
    """
    try:
        # permission: allow if the requester is the student or an admin
        role = getattr(current_user, 'role', None)
        role_name = None
        if isinstance(role, dict):
            role_name = role.get('name')
        elif isinstance(role, str):
            role_name = role

        current_id = getattr(current_user, 'id', None) or getattr(current_user, 'uid', None) or None
        if not (str(current_id) == str(student_id) or (role_name and str(role_name) == 'admin')):
            raise HTTPException(status_code=403, detail='Not allowed to access this student dashboard')

        # Fetch student profile
        student = get_doc('students', student_id) or {}

        # Academic summary: use enrollments and optional credits/grades fields
        academic = {
            'credits_required': student.get('credits_required') or 0,
            'credits_validated': 0,
            'ue_validated': 0,
            'ue_total': 0,
            'average': None,
            'status': 'Unknown',
        }
        enrolls = []
        try:
            enrolls = list_docs('enrollments', where=[('student_id', '==', str(student_id))], limit=5000) or []
        except Exception:
            enrolls = []

        double_grades = []
        for e in enrolls:
            status = (e.get('status') or '').lower()
            credits = 0
            try:
                credits = int(e.get('credits', 0) or 0)
            except Exception:
                try:
                    credits = int(float(e.get('credits', 0) or 0))
                except Exception:
                    credits = 0
            academic['ue_total'] += 1
            if status in ('passed', 'validated', 'validated_with_compensation', 'success'):
                academic['ue_validated'] += 1
                academic['credits_validated'] = academic.get('credits_validated', 0) + credits
            # collect grades if present
            try:
                if e.get('grade') is not None:
                    double_grades.append(float(e.get('grade')))
            except Exception:
                pass

        if double_grades:
            try:
                academic['average'] = sum(double_grades) / len(double_grades)
            except Exception:
                academic['average'] = None

        # Simple academic status rule
        try:
            req = int(student.get('credits_required') or academic['credits_required'] or 0)
            validated = int(academic.get('credits_validated') or 0)
            if req > 0 and validated >= req:
                academic['status'] = 'OK'
            elif validated == 0:
                academic['status'] = 'Conditionnel'
            else:
                academic['status'] = 'Conditionnel'
        except Exception:
            academic['status'] = academic.get('status', 'Unknown')

        # Financial summary
        financial = {
            'fees_total': 0.0,
            'paid': 0.0,
            'balance': 0.0,
            'exam_access': True,
        }
        try:
            fees_total = float(student.get('fees_total') or student.get('tuition') or 0.0)
        except Exception:
            fees_total = 0.0
        payments = []
        try:
            payments = list_docs('payments', where=[('student_id', '==', str(student_id))], limit=5000) or []
        except Exception:
            payments = []
        paid_sum = 0.0
        for p in payments:
            try:
                paid_sum += float(p.get('amount', 0) or 0)
            except Exception:
                pass
        financial['fees_total'] = fees_total
        financial['paid'] = paid_sum
        financial['balance'] = round(fees_total - paid_sum, 2)
        financial['exam_access'] = financial['balance'] <= 0.0

        # Recent notifications (limit 5)
        recent_notifications = []
        try:
            recent_notifications = list_docs('notifications', where=[('recipient_id', '==', str(student_id))], limit=10) or []
            # sort by created_at desc if possible
            try:
                recent_notifications = sorted(recent_notifications, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
            except Exception:
                recent_notifications = recent_notifications[:5]
        except Exception:
            recent_notifications = []

        # Next exams: attempt to collect exam documents linked to student's program/promotion or explicit student_id
        next_exams = []
        try:
            # Prefer exams that explicitly target the student
            exams = list_docs('exams', where=[('student_id', '==', str(student_id))], limit=50) or []
            if not exams:
                # fallback: exams by program/promotion
                prog = student.get('program_id')
                prom = student.get('promotion_id')
                q = []
                if prog:
                    q.append(('program_id', '==', str(prog)))
                if prom:
                    q.append(('promotion_id', '==', str(prom)))
                if q:
                    exams = list_docs('exams', where=q, limit=50) or []
            # minimal normalization
            for ex in exams:
                next_exams.append({
                    'id': ex.get('id') or ex.get('exam_id') or None,
                    'title': ex.get('title') or ex.get('name') or 'Examen',
                    'date': ex.get('date') or ex.get('datetime') or None,
                    'ue_code': ex.get('ue_code') or ex.get('ue_id') or None,
                    'room': ex.get('room') or None,
                })
        except Exception:
            next_exams = []

        # Build compact payload for mobile
        payload = {
            'ok': True,
            'student': student,
            'academic': academic,
            'financial': financial,
            'recent_notifications': recent_notifications,
            'next_exams': next_exams,
        }
        return payload
    except HTTPException:
        # re-raise permission and other HTTP errors
        raise
    except Exception as e:
        logging.exception('Error building student dashboard for %s: %s', student_id, e)
        return {'ok': False, 'error': str(e), 'student': {}, 'academic': {}, 'financial': {}, 'recent_notifications': [], 'next_exams': []}
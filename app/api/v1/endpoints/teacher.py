"""
Endpoints dédiés aux enseignants : dashboard, gestion des cours, étudiants par UE, notes, examens,
supports pédagogiques, annonces/communication, notifications et gestion de profil.
Conçu pour être défensif et similaire à students.py.
"""
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from datetime import datetime, timedelta
import logging

from firebase_admin import firestore, messaging, auth

from app.core.security import get_current_active_user
from app.models.firestore_models import get_doc, list_docs
from app.core.config import settings
from pydantic import BaseModel, Field
from app.api.v1.endpoints.users import generate_random_password

router = APIRouter()


# Simple models
class GradeCreate(BaseModel):
    student_id: str
    ue_id: str
    grade: Optional[float]
    type: Optional[str] = 'exam'  # exam|cc|tp
    session: Optional[str] = None


class BulkGrades(BaseModel):
    grades: List[GradeCreate]


class MaterialCreate(BaseModel):
    title: str
    url: Optional[str] = None
    storage_path: Optional[str] = None
    visibility: Optional[str] = 'students'  # students|public|teachers
    description: Optional[str] = None


class AnnouncementCreate(BaseModel):
    title: str
    body: str
    target: Optional[str] = 'class'  # class|ue|student
    target_id: Optional[str] = None
    data: Optional[Dict[str, str]] = None
    silent: Optional[bool] = False


class TeacherCreate(BaseModel):
    email: str
    password: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    phone: str | None = None
    gender: str | None = None
    matricule: str | None = None
    birthdate: str | None = None
    faculty_id: str | None = None
    department_id: str | None = None
    program_id: str | None = None
    promotion_id: str | None = None
    group_id: str | None = None
    photo_base64: str | None = None
    photo_filename: str | None = None
    username: str | None = None


class TeacherUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    phone: str | None = None
    gender: str | None = None
    matricule: str | None = None
    birthdate: str | None = None
    faculty_id: str | None = None
    department_id: str | None = None
    program_id: str | None = None
    promotion_id: str | None = None
    group_id: str | None = None
    photo_base64: str | None = None
    photo_filename: str | None = None
    username: str | None = None


# Helpers
def _is_allowed_teacher(teacher_id: str, current_user: Any) -> bool:
    try:
        role = getattr(current_user, 'role', None)
        if isinstance(role, dict):
            role_name = role.get('name')
        else:
            role_name = role
        current_id = getattr(current_user, 'id', None) or getattr(current_user, 'uid', None) or None
        if str(current_id) == str(teacher_id):
            return True
        if role_name and str(role_name).lower() == 'admin':
            return True
        return False
    except Exception:
        return False


def _safe_float(v, default=0.0):
    try:
        return float(v or 0)
    except Exception:
        return default


def _safe_int(v, default=0):
    try:
        return int(v or 0)
    except Exception:
        return default


def _parse_iso_datetime(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
    return None


def _cap_limit(limit: int, max_allowed: int = 5000) -> int:
    try:
        l = int(limit)
    except Exception:
        return min(max_allowed, 1000)
    return min(max_allowed, max(1, l))


def _audit(action: str, by: Any, meta: Dict[str, Any]):
    try:
        db = firestore.client()
        db.collection('audit_logs').document().set({
            'action': action,
            'by': getattr(by, 'id', None) or getattr(by, 'uid', None),
            'meta': meta,
            'created_at': firestore.SERVER_TIMESTAMP,
        })
    except Exception:
        logging.exception('Failed to write audit log')


# Endpoints
@router.get('/teachers/{teacher_id}/dashboard')
async def teacher_dashboard(teacher_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    """Enseignant dashboard: synthèse mobile+desktop"""
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed to access this teacher dashboard')
    try:
        teacher = get_doc('teachers', teacher_id) or {}
        if not teacher:
            return {'ok': False, 'error': 'Teacher not found', 'teacher': {}, 'profile': {}, 'summary': {}}

        # basic profile
        profile = {
            'id': teacher_id,
            'full_name': teacher.get('full_name') or f"{teacher.get('first_name','')} {teacher.get('last_name','') }".strip(),
            'photo_url': teacher.get('photo_url') or teacher.get('avatar_url'),
            'department': teacher.get('department'),
            'faculty': teacher.get('faculty'),
            'status': teacher.get('status', 'active'),
            'academic_year': teacher.get('academic_year') or settings.get('DEFAULT_ACADEMIC_YEAR', None),
        }

        # courses
        courses = list_docs('ues', where=[('teacher_id', '==', str(teacher_id))], limit=_cap_limit(200)) or []
        course_count = len(courses)

        # students count across courses (best-effort)
        student_ids = set()
        notes_to_encode = 0
        upcoming = []
        try:
            for c in courses:
                enrs = list_docs('enrollments', where=[('ue_id', '==', str(c.get('id') or c.get('ue_code')))], limit=_cap_limit(2000)) or []
                for e in enrs:
                    student_ids.add(str(e.get('student_id')))
                # pending grades heuristic
                grades_pending = list_docs('grades', where=[('ue_id', '==', str(c.get('id') or c.get('ue_code')),), ('validated', '==', False)], limit=_cap_limit(1000)) or []
                notes_to_encode += len(grades_pending)
        except Exception:
            pass

        # exams / next sessions
        try:
            now = datetime.utcnow()
            exams = list_docs('exams', where=[('teacher_id', '==', str(teacher_id))], limit=_cap_limit(200)) or []
            for ex in exams:
                d = ex.get('date') or ex.get('datetime')
                dobj = _parse_iso_datetime(d)
                if dobj and dobj >= now:
                    upcoming.append({'exam': ex, 'date': d})
        except Exception:
            upcoming = []

        # notifications count
        notifications = list_docs('notifications', where=[('recipient_teacher_id', '==', str(teacher_id))], limit=20) or []

        summary = {
            'course_count': course_count,
            'total_students': len(student_ids),
            'notes_to_encode': notes_to_encode,
            'upcoming_exams': upcoming[:10],
            'notifications': sorted(notifications, key=lambda x: x.get('created_at',''), reverse=True)[:10]
        }

        return {'ok': True, 'teacher': profile, 'profile': profile, 'summary': summary}
    except Exception as e:
        logging.exception('Error building teacher dashboard %s: %s', teacher_id, e)
        return {'ok': False, 'error': str(e), 'teacher': {}, 'profile': {}, 'summary': {}}


@router.get('/teachers/{teacher_id}/courses')
async def teacher_courses(teacher_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        courses = list_docs('ues', where=[('teacher_id', '==', str(teacher_id))], limit=_cap_limit(1000)) or []
        # attach student counts
        for c in courses:
            try:
                enrs = list_docs('enrollments', where=[('ue_id', '==', str(c.get('id') or c.get('ue_code')))], limit=_cap_limit(5000)) or []
                c['student_count'] = len(enrs)
            except Exception:
                c['student_count'] = 0
        return {'ok': True, 'courses': courses}
    except Exception as e:
        logging.exception('Error listing teacher courses %s: %s', teacher_id, e)
        return {'ok': False, 'error': str(e), 'courses': []}


@router.get('/teachers/{teacher_id}/courses/{course_id}')
async def teacher_course_detail(teacher_id: str, course_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        c = get_doc('ues', course_id) or {}
        if not c:
            return {'ok': False, 'error': 'Course not found', 'course': {}}
        # ensure ownership unless admin
        if str(c.get('teacher_id')) != str(teacher_id) and getattr(current_user, 'role', None) != 'admin':
            raise HTTPException(status_code=403, detail='Not allowed to access this course')
        # attach meta
        try:
            enrs = list_docs('enrollments', where=[('ue_id', '==', str(course_id))], limit=_cap_limit(5000)) or []
        except Exception:
            enrs = []
        c['student_count'] = len(enrs)
        return {'ok': True, 'course': c, 'enrollments': enrs}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception('Error fetching course detail %s: %s', course_id, e)
        return {'ok': False, 'error': str(e), 'course': {}, 'enrollments': []}


@router.get('/teachers/{teacher_id}/courses/{course_id}/students')
async def course_students(teacher_id: str, course_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        enrolls = list_docs('enrollments', where=[('ue_id', '==', str(course_id))], limit=_cap_limit(5000)) or []
        students = []
        for e in enrolls:
            sid = e.get('student_id')
            s = get_doc('students', str(sid)) or {}
            students.append({'enrollment': e, 'student': s})
        return {'ok': True, 'students': students}
    except Exception as e:
        logging.exception('Error listing course students %s: %s', course_id, e)
        return {'ok': False, 'error': str(e), 'students': []}


@router.get('/teachers/{teacher_id}/courses/{course_id}/grades')
async def course_grades(teacher_id: str, course_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        grades = list_docs('grades', where=[('ue_id', '==', str(course_id))], limit=_cap_limit(5000)) or []
        return {'ok': True, 'grades': grades}
    except Exception as e:
        logging.exception('Error listing grades for %s: %s', course_id, e)
        return {'ok': False, 'error': str(e), 'grades': []}


@router.post('/teachers/{teacher_id}/courses/{course_id}/grades', summary='Create or update a grade')
async def create_or_update_grade(teacher_id: str, course_id: str, payload: GradeCreate, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        # permission check: teacher must own the course unless admin
        course = get_doc('ues', course_id) or {}
        if course and str(course.get('teacher_id')) != str(teacher_id) and getattr(current_user, 'role', None) != 'admin':
            raise HTTPException(status_code=403, detail='Not allowed to modify grades for this course')

        db = firestore.client()
        # create/update grade doc keyed by student+ue+type+session
        query_id = f"{payload.student_id}_{course_id}_{payload.type or 'exam'}_{payload.session or 'default'}"
        doc_ref = db.collection('grades').document(query_id)
        doc = {
            'student_id': str(payload.student_id),
            'ue_id': str(course_id),
            'grade': payload.grade,
            'type': payload.type,
            'session': payload.session,
            'validated': False,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'updated_by': getattr(current_user, 'id', None) or getattr(current_user, 'uid', None),
        }
        doc_ref.set(doc, merge=True)
        _audit('grade_upsert', current_user, {'grade_id': query_id, 'course_id': course_id, 'student_id': payload.student_id})
        return {'ok': True, 'grade_id': query_id, 'grade': doc}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception('Error creating/updating grade %s: %s', course_id, e)
        return {'ok': False, 'error': str(e)}


@router.post('/teachers/{teacher_id}/courses/{course_id}/grades/bulk', summary='Bulk import grades (JSON payload)')
async def bulk_import_grades(teacher_id: str, course_id: str, payload: BulkGrades, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        course = get_doc('ues', course_id) or {}
        if course and str(course.get('teacher_id')) != str(teacher_id) and getattr(current_user, 'role', None) != 'admin':
            raise HTTPException(status_code=403, detail='Not allowed to import grades for this course')
        db = firestore.client()
        results = {'ok': True, 'imported': 0, 'errors': []}
        for g in payload.grades:
            try:
                query_id = f"{g.student_id}_{course_id}_{g.type or 'exam'}_{g.session or 'default'}"
                doc_ref = db.collection('grades').document(query_id)
                doc = {
                    'student_id': str(g.student_id),
                    'ue_id': str(course_id),
                    'grade': g.grade,
                    'type': g.type,
                    'session': g.session,
                    'validated': False,
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'updated_by': getattr(current_user, 'id', None) or getattr(current_user, 'uid', None),
                }
                doc_ref.set(doc, merge=True)
                results['imported'] += 1
            except Exception as ex:
                logging.exception('Error importing grade for %s in %s: %s', g.student_id, course_id, ex)
                results['errors'].append({'student': g.student_id, 'error': str(ex)})
        _audit('grades_bulk_import', current_user, {'course_id': course_id, 'imported': results['imported']})
        return results
    except HTTPException:
        raise
    except Exception as e:
        logging.exception('Bulk import error %s: %s', course_id, e)
        return {'ok': False, 'error': str(e)}


@router.get('/teachers/{teacher_id}/exams')
async def teacher_exams(teacher_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        exams = list_docs('exams', where=[('teacher_id', '==', str(teacher_id))], limit=_cap_limit(500)) or []
        return {'ok': True, 'exams': exams}
    except Exception as e:
        logging.exception('Error listing exams for teacher %s: %s', teacher_id, e)
        return {'ok': False, 'error': str(e), 'exams': []}


@router.post('/teachers/{teacher_id}/materials', summary='Add course material')
async def add_material(teacher_id: str, payload: MaterialCreate, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        db = firestore.client()
        doc = payload.model_dump()
        doc['teacher_id'] = str(teacher_id)
        doc['created_at'] = firestore.SERVER_TIMESTAMP
        ref = db.collection('materials').document()
        ref.set(doc)
        _audit('material_create', current_user, {'material_id': ref.id})
        return {'ok': True, 'material_id': ref.id, 'material': doc}
    except Exception as e:
        logging.exception('Error adding material for %s: %s', teacher_id, e)
        return {'ok': False, 'error': str(e)}


@router.get('/teachers/{teacher_id}/materials')
async def list_materials(teacher_id: str, course_id: Optional[str] = None, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        q = [('teacher_id', '==', str(teacher_id))]
        if course_id:
            q.append(('ue_id', '==', str(course_id)))
        mats = list_docs('materials', where=q, limit=_cap_limit(500)) or []
        return {'ok': True, 'materials': mats}
    except Exception as e:
        logging.exception('Error listing materials for %s: %s', teacher_id, e)
        return {'ok': False, 'error': str(e), 'materials': []}


@router.post('/teachers/{teacher_id}/announce', summary='Create an announcement / send notification')
async def create_announcement(teacher_id: str, payload: AnnouncementCreate, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user) and getattr(current_user, 'role', None) != 'admin':
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        db = firestore.client()
        ann = payload.model_dump()
        ann['teacher_id'] = str(teacher_id)
        ann['created_at'] = firestore.SERVER_TIMESTAMP
        ann['created_by'] = getattr(current_user, 'id', None) or getattr(current_user, 'uid', None)
        ref = db.collection('announcements').document()
        ref.set(ann)

        # determine recipients and tokens
        tokens = []
        if payload.target == 'student' and payload.target_id:
            tokens_docs = list_docs('device_tokens', where=[('student_id', '==', str(payload.target_id))], limit=500) or []
            tokens = [t.get('token') for t in tokens_docs if t.get('token')]
        elif payload.target == 'ue' and payload.target_id:
            # all students in UE
            enrs = list_docs('enrollments', where=[('ue_id', '==', str(payload.target_id))], limit=_cap_limit(5000)) or []
            sids = set([str(e.get('student_id')) for e in enrs if e.get('student_id')])
            if sids:
                tokens_docs = list_docs('device_tokens', where=[('student_id', 'in', list(sids))], limit=_cap_limit(5000)) or []
                tokens = [t.get('token') for t in tokens_docs if t.get('token')]
        else:
            # class/department broad send: best-effort fetch tokens for teacher's students
            enrs = []
            try:
                courses = list_docs('ues', where=[('teacher_id', '==', str(teacher_id))], limit=_cap_limit(200)) or []
                for c in courses:
                    e = list_docs('enrollments', where=[('ue_id', '==', str(c.get('id') or c.get('ue_code')))], limit=_cap_limit(2000)) or []
                    enrs.extend(e)
                sids = set([str(x.get('student_id')) for x in enrs if x.get('student_id')])
                if sids:
                    tokens_docs = list_docs('device_tokens', where=[('student_id', 'in', list(sids))], limit=_cap_limit(5000)) or []
                    tokens = [t.get('token') for t in tokens_docs if t.get('token')]
            except Exception:
                tokens = []

        # send via FCM
        if tokens:
            try:
                message = messaging.MulticastMessage(
                    notification=messaging.Notification(title=payload.title, body=payload.body) if not payload.silent else None,
                    data={k: str(v) for k, v in (payload.data or {}).items()},
                    tokens=tokens,
                )
                resp = messaging.send_multicast(message)
                if resp.failure_count > 0:
                    invalid_indexes = [i for i, r in enumerate(resp.responses) if not r.success]
                    for idx in invalid_indexes:
                        tok = tokens[idx]
                        try:
                            db.collection('device_tokens').document(tok).delete()
                        except Exception:
                            pass
                _audit('announcement_send', current_user, {'announcement_id': ref.id, 'sent': resp.success_count})
                return {'ok': True, 'announcement_id': ref.id, 'fcm': {'success': resp.success_count, 'failure': resp.failure_count}}
            except Exception as e:
                logging.exception('Error sending announcement via FCM: %s', e)
                return {'ok': False, 'error': 'Failed to send push', 'announcement_id': ref.id}
        else:
            return {'ok': True, 'announcement_id': ref.id, 'message': 'No device tokens found'}
    except Exception as e:
        logging.exception('Error creating announcement: %s', e)
        return {'ok': False, 'error': str(e)}


@router.put('/teachers/{teacher_id}/profile')
async def update_teacher_profile(teacher_id: str, payload: Dict[str, Any], current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        db = firestore.client()
        ref = db.collection('teachers').document(str(teacher_id))
        if not ref.get().exists:
            raise HTTPException(status_code=404, detail='Teacher not found')
        payload['updated_at'] = firestore.SERVER_TIMESTAMP
        ref.update(payload)
        _audit('teacher_update_profile', current_user, {'teacher_id': teacher_id})
        return {'ok': True, 'message': 'Profile updated', 'updates': payload}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception('Error updating teacher profile %s: %s', teacher_id, e)
        return {'ok': False, 'error': str(e)}


@router.post('/teachers/{teacher_id}/devices')
async def register_device_token(teacher_id: str, payload: Dict[str, Any], current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user) and getattr(current_user, 'role', None) != 'admin':
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        db = firestore.client()
        token = payload.get('token')
        if not token:
            raise HTTPException(status_code=400, detail='Token missing')
        doc = {'teacher_id': str(teacher_id), 'token': token, 'platform': payload.get('platform'), 'name': payload.get('name'), 'created_at': firestore.SERVER_TIMESTAMP}
        db.collection('device_tokens').document(token).set(doc, merge=True)
        return {'ok': True, 'token': token}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception('Error registering teacher device token %s: %s', teacher_id, e)
        return {'ok': False, 'error': str(e)}


@router.delete('/teachers/{teacher_id}/devices/{token}')
async def unregister_device_token(teacher_id: str, token: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user) and getattr(current_user, 'role', None) != 'admin':
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        db = firestore.client()
        ref = db.collection('device_tokens').document(token)
        if ref.get().exists:
            data = ref.get().to_dict() or {}
            if str(data.get('teacher_id')) != str(teacher_id):
                raise HTTPException(status_code=403, detail='Token does not belong to this teacher')
            ref.delete()
        return {'ok': True}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception('Error unregistering teacher token %s: %s', token, e)
        return {'ok': False, 'error': str(e)}


@router.get('/teachers/{teacher_id}/statistics')
async def teacher_statistics(teacher_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_teacher(teacher_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        # simple aggregated stats: avg per UE, failure rates
        stats = {}
        courses = list_docs('ues', where=[('teacher_id', '==', str(teacher_id))], limit=_cap_limit(200)) or []
        for c in courses:
            try:
                grades = list_docs('grades', where=[('ue_id', '==', str(c.get('id') or c.get('ue_code')))], limit=_cap_limit(5000)) or []
                numeric = [ _safe_float(g.get('grade')) for g in grades if g.get('grade') is not None ]
                avg = round(sum(numeric)/len(numeric),2) if numeric else None
                failures = len([x for x in numeric if x < float(getattr(settings, 'PASS_THRESHOLD', 10))])
                stats[c.get('id') or c.get('ue_code') or c.get('title','unknown')] = {'average': avg, 'count': len(numeric), 'failures': failures}
            except Exception:
                stats[c.get('id') or c.get('ue_code') or 'unknown'] = {'average': None, 'count': 0, 'failures': 0}
        return {'ok': True, 'statistics': stats}
    except Exception as e:
        logging.exception('Error computing statistics for %s: %s', teacher_id, e)
        return {'ok': False, 'error': str(e), 'statistics': {}}


@router.post('/teachers', summary='Créer un enseignant avec Auth')
async def create_teacher(teacher: TeacherCreate, current_user: Any = Depends(get_current_active_user)):
    db = firestore.client()
    password = teacher.password or generate_random_password()
    try:
        user_record = auth.create_user(
            email=teacher.email,
            password=password,
            display_name=f"{teacher.first_name or ''} {teacher.last_name or ''}".strip(),
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail=f"L'email '{teacher.email}' est déjà utilisé par un autre compte.")
    user_profile_data = {
        "firebase_uid": user_record.uid,
        "email": teacher.email,
        "display_name": f"{teacher.first_name or ''} {teacher.last_name or ''}".strip(),
        "first_name": teacher.first_name,
        "last_name": teacher.last_name,
        "role": "teacher",
        "created_at": firestore.SERVER_TIMESTAMP,
        "is_active": True,
    }
    db.collection("users").document(user_record.uid).set(user_profile_data, merge=True)
    teacher_data = teacher.model_dump(exclude_unset=True)
    teacher_data["auth_uid"] = user_record.uid
    teacher_data["created_at"] = firestore.SERVER_TIMESTAMP
    teacher_data["updated_at"] = firestore.SERVER_TIMESTAMP
    db.collection("teachers").document(user_record.uid).set(teacher_data, merge=True)
    return {"ok": True, "uid": user_record.uid, "email": user_record.email, "generated_password": password if teacher.password is None else None}


@router.put('/teachers/{teacher_id}', summary='Mettre à jour un enseignant avec Auth')
async def update_teacher(
    teacher_id: str = Path(..., description='UID Firebase ou ID enseignant'),
    teacher: TeacherUpdate = Body(...),
    current_user: Any = Depends(get_current_active_user)
):
    db = firestore.client()
    auth_updates = {}
    if teacher.email:
        auth_updates['email'] = teacher.email
    if teacher.first_name or teacher.last_name:
        full_name = f"{teacher.first_name or ''} {teacher.last_name or ''}".strip()
        auth_updates['display_name'] = full_name
    if teacher.password:
        auth_updates['password'] = teacher.password
    if auth_updates:
        try:
            auth.update_user(teacher_id, **auth_updates)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f'Erreur mise à jour Auth: {e}')
    user_ref = db.collection('users').document(teacher_id)
    user_updates = teacher.model_dump(exclude_unset=True)
    if 'password' in user_updates:
        user_updates.pop('password')
    user_updates['updated_at'] = firestore.SERVER_TIMESTAMP
    user_ref.set(user_updates, merge=True)
    teacher_ref = db.collection('teachers').document(teacher_id)
    teacher_updates = teacher.model_dump(exclude_unset=True)
    if 'password' in teacher_updates:
        teacher_updates.pop('password')
    teacher_updates['updated_at'] = firestore.SERVER_TIMESTAMP
    teacher_ref.set(teacher_updates, merge=True)
    return {"ok": True, "teacher_id": teacher_id}

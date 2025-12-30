"""
Endpoints dédiés aux étudiants : dashboard mobile-first, academic progression, UEs, notes, examens, paiements,
documents et notifications. Conçu pour être défensif et renvoyer toujours une structure cohérente.
"""
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from datetime import datetime, timedelta
import logging

from firebase_admin import firestore, messaging, auth

from app.core.security import get_current_active_user
from app.models.firestore_models import get_doc, list_docs
from app.core.config import settings
from pydantic import BaseModel, Field
from app.api.v1.endpoints.users import generate_random_password


router = APIRouter()


# Small models for updates and tickets
class StudentProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class TicketCreate(BaseModel):
    subject: str
    message: str
    category: Optional[str] = 'support'


class DeviceTokenCreate(BaseModel):
    token: str
    platform: Optional[str] = Field(None, description='android|ios|web')
    name: Optional[str] = None


class NotificationCreate(BaseModel):
    title: str
    body: str
    data: Optional[Dict[str, str]] = None
    silent: Optional[bool] = False


class StudentCreate(BaseModel):
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


class StudentUpdate(BaseModel):
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


# Helper utilities
def _is_allowed_student(student_id: str, current_user: Any) -> bool:
    try:
        role = getattr(current_user, 'role', None)
        if isinstance(role, dict):
            role_name = role.get('name')
        else:
            role_name = role
        current_id = getattr(current_user, 'id', None) or getattr(current_user, 'uid', None) or None
        if str(current_id) == str(student_id):
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
        # try common alternative formats
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


# Core endpoints
@router.get('/students/{student_id}/dashboard')
async def student_dashboard(student_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    """Compact mobile-first dashboard for a student. Always returns a consistent object.
    Accessible to the student themself or admin users.
    """
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed to access this student dashboard')

    try:
        student = get_doc('students', student_id) or {}
        # If no student found, return structured empty response
        if not student:
            return {'ok': False, 'error': 'Student not found', 'student': {}, 'academic': {}, 'ues': [], 'grades': [], 'financial': {}, 'payments': [], 'documents': [], 'notifications': [], 'next_exams': []}

        # Basic profile fields for mobile header
        profile = {
            'id': student_id,
            'full_name': student.get('full_name') or f"{student.get('first_name','') } {student.get('last_name','') }".strip(),
            'matricule': student.get('matricule'),
            'program_id': student.get('program_id'),
            'program_name': None,
            'promotion_id': student.get('promotion_id'),
            'promotion_name': None,
            'academic_year': student.get('academic_year') or settings.get('DEFAULT_ACADEMIC_YEAR', None),
            'avatar_url': student.get('avatar_url') or student.get('photo_url') or None,
        }
        # Resolve program/promotion names defensively
        try:
            if profile['program_id']:
                pdoc = get_doc('programs', str(profile['program_id'])) or {}
                profile['program_name'] = pdoc.get('name') or pdoc.get('title')
        except Exception:
            profile['program_name'] = None
        try:
            if profile['promotion_id']:
                pr = get_doc('promotions', str(profile['promotion_id'])) or {}
                profile['promotion_name'] = pr.get('name') or pr.get('label')
        except Exception:
            profile['promotion_name'] = None

        # Academic summary
        academic = {
            'credits_required': _safe_int(student.get('credits_required') or student.get('creditsNeeded') or 0),
            'credits_validated': 0,
            'ue_validated': 0,
            'ue_total': 0,
            'average': None,
            'status': 'Unknown',
            'years': [],
        }

        enrolls = []
        try:
            enrolls = list_docs('enrollments', where=[('student_id', '==', str(student_id))], limit=_cap_limit(5000)) or []
        except Exception:
            enrolls = []

        years_map: Dict[str, Dict[str, Any]] = {}
        grades_col = []
        for e in enrolls:
            year = str(e.get('academic_year') or e.get('year') or 'unknown')
            years_map.setdefault(year, {'ue_total': 0, 'ue_validated': 0, 'ue_debt': 0, 'ues': []})
            years_map[year]['ue_total'] += 1
            status = (e.get('status') or '').lower()
            credits = _safe_int(e.get('credits', 0))
            if status in ('passed', 'validated', 'validated_with_compensation', 'success'):
                years_map[year]['ue_validated'] += 1
                academic['credits_validated'] = academic.get('credits_validated', 0) + credits
            else:
                years_map[year]['ue_debt'] += 1
            # enrich ue meta
            ue_id = e.get('ue_id') or e.get('ue') or e.get('ue_code')
            ue_meta = {}
            if ue_id:
                try:
                    ue_meta = get_doc('ues', str(ue_id)) or {}
                except Exception:
                    ue_meta = {}
            years_map[year]['ues'].append({'enrollment': e, 'ue': ue_meta})
            academic['ue_total'] += 1
            if status in ('passed', 'validated', 'validated_with_compensation', 'success'):
                academic['ue_validated'] += 1
            try:
                if e.get('grade') is not None:
                    grades_col.append(float(e.get('grade')))
            except Exception:
                pass

        # average
        if grades_col:
            try:
                academic['average'] = round(sum(grades_col) / len(grades_col), 2)
            except Exception:
                academic['average'] = None

        # academic status rules (simple, extensible)
        try:
            req = int(academic.get('credits_required') or 0)
            validated = int(academic.get('credits_validated') or 0)
            if req > 0 and validated >= req:
                academic['status'] = 'OK'
            elif academic.get('ue_debt', 0) if isinstance(academic.get('ue_debt', None), int) else 0:
                academic['status'] = 'Conditionnel'
            else:
                academic['status'] = 'Conditionnel'
        except Exception:
            academic['status'] = academic.get('status', 'Unknown')

        # convert years_map to list sorted
        for y in sorted(years_map.keys()):
            v = years_map[y]
            pct = 0
            try:
                pct = int((v['ue_validated'] / max(1, v['ue_total'])) * 100)
            except Exception:
                pct = 0
            academic['years'].append({'year': y, 'ue_total': v['ue_total'], 'ue_validated': v['ue_validated'], 'ue_debt': v['ue_debt'], 'progress_pct': pct, 'ues': v['ues']})

        # UEs list (compact)
        ues = []
        try:
            ue_ids = set()
            for e in enrolls:
                uid = e.get('ue_id') or e.get('ue') or e.get('ue_code')
                if uid:
                    ue_ids.add(str(uid))
            for uid in ue_ids:
                u = get_doc('ues', uid) or {}
                status = 'unknown'
                for e in enrolls:
                    if str(e.get('ue_id') or e.get('ue') or e.get('ue_code') or '') == uid:
                        status = e.get('status') or status
                teacher = None
                try:
                    tid = u.get('teacher_id') or u.get('teacher')
                    if tid:
                        teacher = get_doc('teachers', str(tid)) or None
                except Exception:
                    teacher = None
                ues.append({'id': uid, 'meta': u, 'status': status, 'teacher': teacher})
        except Exception:
            ues = []

        # Grades (detailed)
        grades = []
        try:
            grades = list_docs('grades', where=[('student_id', '==', str(student_id))], limit=_cap_limit(5000)) or []
        except Exception:
            grades = []

        # Payments
        payments = []
        try:
            payments = list_docs('payments', where=[('student_id', '==', str(student_id))], limit=_cap_limit(2000)) or []
        except Exception:
            payments = []
        paid_sum = sum([_safe_float(p.get('amount', 0)) for p in payments])
        fees_total = _safe_float(student.get('fees_total') or student.get('tuition') or 0.0)
        financial = {
            'fees_total': round(fees_total, 2),
            'paid': round(paid_sum, 2),
            'balance': round(fees_total - paid_sum, 2),
            'exam_access': (fees_total - paid_sum) <= 0.0,
        }

        # Documents
        documents = []
        try:
            documents = list_docs('documents', where=[('student_id', '==', str(student_id))], limit=_cap_limit(500)) or []
        except Exception:
            documents = []

        # Notifications
        notifications = []
        try:
            notifications = list_docs('notifications', where=[('recipient_id', '==', str(student_id))], limit=_cap_limit(20)) or []
            try:
                notifications = sorted(notifications, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
            except Exception:
                notifications = notifications[:10]
        except Exception:
            notifications = []

        # Next exams
        next_exams = []
        try:
            now = datetime.utcnow()
            exams = list_docs('exams', where=[('student_id', '==', str(student_id))], limit=_cap_limit(200)) or []
            if not exams:
                prog = student.get('program_id')
                prom = student.get('promotion_id')
                q = []
                if prog:
                    q.append(('program_id', '==', str(prog)))
                if prom:
                    q.append(('promotion_id', '==', str(prom)))
                if q:
                    exams = list_docs('exams', where=q, limit=_cap_limit(200)) or []
            for ex in exams:
                try:
                    draw = ex.get('date') or ex.get('datetime')
                    dobj = _parse_iso_datetime(draw)
                    upcoming = (dobj is None) or (dobj >= now)
                    next_exams.append({'id': ex.get('id') or ex.get('exam_id'), 'title': ex.get('title') or ex.get('name'), 'date': draw, 'upcoming': upcoming, 'ue': ex.get('ue_id') or ex.get('ue_code'), 'room': ex.get('room')})
                except Exception:
                    continue
        except Exception:
            next_exams = []

        # Alerts & explanations (UX rule: always explain why blocked)
        alerts = []
        try:
            if financial['balance'] > 0:
                alerts.append({'type': 'fees_unpaid', 'message': f"Solde à payer: {financial['balance']}", 'critical': True})
            ue_debts = sum([y.get('ue_debt', 0) for y in years_map.values()])
            if ue_debts > 0:
                alerts.append({'type': 'ue_debt', 'message': f"{ue_debts} UE en dette", 'critical': False})
            # official messages count
            if notifications and len(notifications) > 0:
                alerts.append({'type': 'notifications', 'message': f"{len(notifications)} notifications récentes", 'critical': False})
        except Exception:
            alerts = []

        explanations = []
        try:
            if not financial['exam_access']:
                explanations.append('Accès aux examens bloqué: solde impayé')
            if academic['status'] != 'OK':
                explanations.append(f"Statut académique: {academic['status']} — vérifier les UE non validées et règles de compensation")
        except Exception:
            explanations = []

        payload = {
            'ok': True,
            'student': profile,
            'academic': academic,
            'ues': ues,
            'grades': grades,
            'financial': financial,
            'payments': payments,
            'documents': documents,
            'notifications': notifications,
            'next_exams': next_exams,
            'alerts': alerts,
            'explanations': explanations,
        }
        return payload

    except HTTPException:
        raise
    except Exception as e:
        logging.exception('Error building student dashboard for %s: %s', student_id, e)
        return {'ok': False, 'error': str(e), 'student': {}, 'academic': {}, 'ues': [], 'grades': [], 'financial': {}, 'payments': [], 'documents': [], 'notifications': [], 'next_exams': []}


@router.get('/students/{student_id}/academic')
async def student_academic(student_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    """Detailed academic progression LMD per year and cycle."""
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        student = get_doc('students', student_id) or {}
        if not student:
            return {'ok': False, 'error': 'Student not found', 'student': {}, 'cycles': {}}
        enrolls = list_docs('enrollments', where=[('student_id', '==', str(student_id))], limit=_cap_limit(5000)) or []
        cycles: Dict[str, Dict[str, Any]] = {}
        for e in enrolls:
            cycle = e.get('cycle') or e.get('cycle_type') or 'unknown'
            year = e.get('academic_year') or e.get('year') or 'unknown'
            cycles.setdefault(cycle, {})
            cycles[cycle].setdefault(year, {'ues': [], 'ue_total': 0, 'ue_validated': 0, 'ue_debt': 0})
            entry = cycles[cycle][year]
            entry['ues'].append(e)
            entry['ue_total'] += 1
            status = (e.get('status') or '').lower()
            if status in ('passed', 'validated', 'success'):
                entry['ue_validated'] += 1
            else:
                entry['ue_debt'] += 1
        return {'ok': True, 'student': student, 'cycles': cycles}
    except Exception as e:
        logging.exception('Error in student_academic %s: %s', student_id, e)
        return {'ok': False, 'error': str(e), 'student': {}, 'cycles': {}}


@router.get('/students/{student_id}/ues')
async def student_ues(student_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        enrolls = list_docs('enrollments', where=[('student_id', '==', str(student_id))], limit=_cap_limit(2000)) or []
        ues = []
        for e in enrolls:
            uid = e.get('ue_id') or e.get('ue') or e.get('ue_code')
            meta = {}
            if uid:
                try:
                    meta = get_doc('ues', str(uid)) or {}
                except Exception:
                    meta = {}
            # teacher info
            teacher = None
            try:
                tid = meta.get('teacher_id') or meta.get('teacher')
                if tid:
                    teacher = get_doc('teachers', str(tid)) or None
            except Exception:
                teacher = None
            ues.append({'enrollment': e, 'ue': meta, 'teacher': teacher})
        return {'ok': True, 'ues': ues}
    except Exception as e:
        logging.exception('Error in student_ues %s: %s', student_id, e)
        return {'ok': False, 'error': str(e), 'ues': []}


@router.get('/students/{student_id}/grades')
async def student_grades(student_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        grades = list_docs('grades', where=[('student_id', '==', str(student_id))], limit=_cap_limit(5000)) or []
        sessions: Dict[str, List[Dict]] = {}
        per_ue: Dict[str, List[Dict]] = {}
        for g in grades:
            sess = g.get('session') or g.get('term') or 'unknown'
            sessions.setdefault(sess, []).append(g)
            uid = g.get('ue_id') or g.get('ue') or g.get('ue_code')
            if uid:
                per_ue.setdefault(str(uid), []).append(g)
        # compute simple decisions per UE (pass threshold configurable)
        pass_threshold = getattr(settings, 'PASS_THRESHOLD', 10)
        decisions = {}
        for uid, listg in per_ue.items():
            best = None
            for gg in listg:
                try:
                    val = float(gg.get('grade'))
                    if best is None or val > best:
                        best = val
                except Exception:
                    continue
            status = 'Unknown'
            try:
                if best is not None:
                    status = 'Validé' if float(best) >= float(pass_threshold) else 'Ajourné'
            except Exception:
                status = 'Unknown'
            decisions[uid] = {'best_grade': best, 'status': status}
        return {'ok': True, 'grades': grades, 'by_session': sessions, 'decisions': decisions}
    except Exception as e:
        logging.exception('Error in student_grades %s: %s', student_id, e)
        return {'ok': False, 'error': str(e), 'grades': [], 'by_session': {}, 'decisions': {}}


@router.get('/students/{student_id}/exams')
async def student_exams(student_id: str, upcoming_only: bool = Query(True), limit: int = Query(200), current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        limit = _cap_limit(limit, 1000)
        now = datetime.utcnow()
        exams = list_docs('exams', where=[('student_id', '==', str(student_id))], limit=limit) or []
        if not exams:
            student = get_doc('students', student_id) or {}
            prog = student.get('program_id')
            prom = student.get('promotion_id')
            q = []
            if prog:
                q.append(('program_id', '==', str(prog)))
            if prom:
                q.append(('promotion_id', '==', str(prom)))
            if q:
                exams = list_docs('exams', where=q, limit=limit) or []
        result = []
        for ex in exams:
            try:
                d = ex.get('date') or ex.get('datetime')
                date_obj = _parse_iso_datetime(d)
                if upcoming_only and date_obj and date_obj < now:
                    continue
                # enrich UE and room teacher info
                ue_meta = {}
                try:
                    ue_meta = get_doc('ues', str(ex.get('ue_id') or ex.get('ue') or ex.get('ue_code'))) or {}
                except Exception:
                    ue_meta = {}
                result.append({'exam': ex, 'ue': ue_meta, 'date_obj': date_obj})
            except Exception:
                continue
        return {'ok': True, 'exams': result}
    except Exception as e:
        logging.exception('Error in student_exams %s: %s', student_id, e)
        return {'ok': False, 'error': str(e), 'exams': []}


@router.get('/students/{student_id}/payments')
async def student_payments(student_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        student = get_doc('students', student_id) or {}
        payments = list_docs('payments', where=[('student_id', '==', str(student_id))], limit=_cap_limit(2000)) or []
        paid = sum([_safe_float(p.get('amount', 0)) for p in payments])
        fees_total = _safe_float(student.get('fees_total') or student.get('tuition') or 0.0)
        # attach receipts if documents collection contains receipts linked by payment_id
        receipts = []
        try:
            receipts = list_docs('documents', where=[('student_id', '==', str(student_id)), ('type', '==', 'payment_receipt')], limit=200) or []
            receipts_by_payment = {r.get('payment_id'): r for r in receipts if r.get('payment_id')}
        except Exception:
            receipts_by_payment = {}
        for p in payments:
            pid = p.get('id') or p.get('payment_id')
            if pid and receipts_by_payment.get(pid):
                p['_receipt'] = receipts_by_payment.get(pid)
        summary = {
            'fees_total': round(fees_total, 2),
            'paid': round(paid, 2),
            'balance': round(fees_total - paid, 2),
            'can_access_exams': (fees_total - paid) <= 0.0,
            'payments': payments
        }
        return {'ok': True, 'summary': summary}
    except Exception as e:
        logging.exception('Error in student_payments %s: %s', student_id, e)
        return {'ok': False, 'error': str(e), 'summary': {}}


@router.get('/students/{student_id}/documents')
async def student_documents(student_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        docs = list_docs('documents', where=[('student_id', '==', str(student_id))], limit=_cap_limit(500)) or []
        # normalize files: ensure url or storage pointer present
        for d in docs:
            if not d.get('url') and d.get('storage_path'):
                # best-effort: create a signed url could be here if implemented; fallback to storage_path
                d.setdefault('url', d.get('storage_path'))
        return {'ok': True, 'documents': docs}
    except Exception as e:
        logging.exception('Error in student_documents %s: %s', student_id, e)
        return {'ok': False, 'error': str(e), 'documents': []}


@router.get('/students/{student_id}/notifications')
async def student_notifications(student_id: str, limit: int = Query(20), current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        limit = _cap_limit(limit, 500)
        notifs = list_docs('notifications', where=[('recipient_id', '==', str(student_id))], limit=limit) or []
        try:
            notifs = sorted(notifs, key=lambda x: x.get('created_at', ''), reverse=True)
        except Exception:
            pass
        return {'ok': True, 'notifications': notifs}
    except Exception as e:
        logging.exception('Error in student_notifications %s: %s', student_id, e)
        return {'ok': False, 'error': str(e), 'notifications': []}


@router.put('/students/{student_id}/profile')
async def update_student_profile(student_id: str, payload: StudentProfileUpdate, current_user: Any = Depends(get_current_active_user)) -> Any:
    """Allow a student (or admin) to update their profile fields (non-auth fields)."""
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed to update this profile')
    try:
        db = firestore.client()
        doc_ref = db.collection('students').document(str(student_id))
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail='Student not found')
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return {'ok': True, 'message': 'No changes provided'}
        updates['updated_at'] = firestore.SERVER_TIMESTAMP
        doc_ref.update(updates)
        return {'ok': True, 'message': 'Profile updated', 'updates': updates}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception('Error updating student profile %s: %s', student_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/students/{student_id}/simulate', summary='Simulate LMD decision for a student')
async def simulate_student_decision(student_id: str, consider_compensation: bool = True, current_user: Any = Depends(get_current_active_user)) -> Any:
    """Apply simple rules to determine pass/ajourné/compensation with explanations.
    Returns a decision object with step-by-step explanation suitable for mobile display.
    """
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        grades = list_docs('grades', where=[('student_id', '==', str(student_id))], limit=_cap_limit(5000)) or []
        if not grades:
            return {'ok': True, 'decision': 'No grades', 'explanations': ['Aucune note disponible pour simuler.']}

        # Best grade per UE
        best_per_ue: Dict[str, float] = {}
        for g in grades:
            try:
                uid = str(g.get('ue_id') or g.get('ue') or g.get('ue_code') or '')
                val = float(g.get('grade'))
                if uid:
                    if uid not in best_per_ue or val > best_per_ue[uid]:
                        best_per_ue[uid] = val
            except Exception:
                continue

        total_ues = len(best_per_ue)
        avg = None
        if total_ues > 0:
            avg = round(sum(best_per_ue.values()) / total_ues, 2)

        pass_threshold = getattr(settings, 'PASS_THRESHOLD', 10)
        required_credits = int(get_doc('students', student_id).get('credits_required') or 0) if get_doc('students', student_id) else 0

        ue_failed = [ue for ue, val in best_per_ue.items() if val < float(pass_threshold)]
        failed_count = len(ue_failed)

        explanations: List[str] = []
        explanations.append(f"Moyenne calculée: {avg if avg is not None else 'N/A'} (seuil: {pass_threshold})")
        if failed_count == 0 and (avg is None or avg >= pass_threshold):
            decision = 'Validé'
            explanations.append('Toutes les UE sont au-dessus du seuil. L\'étudiant est validé pour la session.')
        else:
            # Compensation logic (simple)
            compensation_allowed = consider_compensation
            if compensation_allowed and avg is not None and avg >= pass_threshold - 1.0 and failed_count <= 2:
                decision = 'Validé par compensation'
                explanations.append('La moyenne permet une compensation des UE faibles selon la politique paramétrable.')
                explanations.append(f"UE en défaut (max {failed_count}): {', '.join(ue_failed[:10])}")
            else:
                decision = 'Ajourné'
                explanations.append('L\'étudiant n\'atteint pas les critères de validation. Veuillez consulter les UE en dette et les règles de compensation.')
                if ue_failed:
                    explanations.append(f"UE en défaut: {', '.join(ue_failed[:20])}")

        # Provide actionable next steps
        next_steps = []
        if decision != 'Validé':
            next_steps.append('Consulter les UE en dette et planifier des sessions de rattrapage.')
            next_steps.append('Vérifier le règlement LMD pour les règles de compensation et seuils.')
        else:
            next_steps.append('Félicitations — vérifier le relevé officiel dans Documents si nécessaire.')

        return {'ok': True, 'decision': decision, 'average': avg, 'failed_ues': ue_failed, 'explanations': explanations, 'next_steps': next_steps}
    except Exception as e:
        logging.exception('Error simulating decision for %s: %s', student_id, e)
        return {'ok': False, 'error': str(e)}


@router.post('/students/{student_id}/tickets', summary='Create a support ticket for a student')
async def create_ticket(student_id: str, ticket: TicketCreate, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        db = firestore.client()
        doc = {
            'student_id': str(student_id),
            'subject': ticket.subject,
            'message': ticket.message,
            'category': ticket.category or 'support',
            'status': 'open',
            'created_at': firestore.SERVER_TIMESTAMP,
            'created_by': getattr(current_user, 'id', None) or getattr(current_user, 'uid', None)
        }
        ref = db.collection('tickets').document()
        ref.set(doc)
        return {'ok': True, 'ticket_id': ref.id, 'ticket': doc}
    except Exception as e:
        logging.exception('Error creating ticket for %s: %s', student_id, e)
        return {'ok': False, 'error': str(e)}


@router.get('/students/{student_id}/tickets', summary='List support tickets for a student')
async def list_tickets(student_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        docs = list_docs('tickets', where=[('student_id', '==', str(student_id))], limit=_cap_limit(200)) or []
        return {'ok': True, 'tickets': docs}
    except Exception as e:
        logging.exception('Error listing tickets for %s: %s', student_id, e)
        return {'ok': False, 'error': str(e)}


@router.post('/students/{student_id}/devices', summary='Register a device token for push notifications')
async def register_device_token(student_id: str, payload: DeviceTokenCreate, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        db = firestore.client()
        # Use token as document id to avoid duplicates
        doc_ref = db.collection('device_tokens').document(payload.token)
        doc = {
            'student_id': str(student_id),
            'token': payload.token,
            'platform': payload.platform,
            'name': payload.name,
            'created_at': firestore.SERVER_TIMESTAMP,
        }
        doc_ref.set(doc, merge=True)
        return {'ok': True, 'token': payload.token}
    except Exception as e:
        logging.exception('Error registering device token for %s: %s', student_id, e)
        return {'ok': False, 'error': str(e)}


@router.delete('/students/{student_id}/devices/{token}', summary='Unregister a device token')
async def unregister_device_token(student_id: str, token: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        db = firestore.client()
        doc_ref = db.collection('device_tokens').document(token)
        if doc_ref.get().exists:
            doc = doc_ref.get().to_dict() or {}
            if str(doc.get('student_id')) != str(student_id):
                raise HTTPException(status_code=403, detail='Token does not belong to this student')
            doc_ref.delete()
        return {'ok': True}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception('Error unregistering token %s for %s: %s', token, student_id, e)
        return {'ok': False, 'error': str(e)}


@router.get('/students/{student_id}/devices', summary='List device tokens for a student')
async def list_device_tokens(student_id: str, current_user: Any = Depends(get_current_active_user)) -> Any:
    if not _is_allowed_student(student_id, current_user):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        docs = list_docs('device_tokens', where=[('student_id', '==', str(student_id))], limit=_cap_limit(100)) or []
        return {'ok': True, 'tokens': docs}
    except Exception as e:
        logging.exception('Error listing device tokens for %s: %s', student_id, e)
        return {'ok': False, 'error': str(e)}


@router.post('/students/{student_id}/notify', summary='Send a push notification to a student (also saves to notifications collection)')
async def send_notification_to_student(student_id: str, payload: NotificationCreate, current_user: Any = Depends(get_current_active_user)) -> Any:
    # Allow student to send to self (e.g., preference-driven) or allow admins to send to any student
    if not (_is_allowed_student(student_id, current_user) or getattr(current_user, 'role', None) == 'admin'):
        raise HTTPException(status_code=403, detail='Not allowed')
    try:
        db = firestore.client()
        # create notification doc
        notif = {
            'recipient_id': str(student_id),
            'title': payload.title,
            'body': payload.body,
            'data': payload.data or {},
            'silent': payload.silent,
            'created_at': firestore.SERVER_TIMESTAMP,
            'created_by': getattr(current_user, 'id', None) or getattr(current_user, 'uid', None)
        }
        nref = db.collection('notifications').document()
        nref.set(notif)

        # fetch device tokens
        tokens_docs = list_docs('device_tokens', where=[('student_id', '==', str(student_id))], limit=500) or []
        tokens = [t.get('token') for t in tokens_docs if t.get('token')]
        if tokens:
            # send via FCM in batches using send_multicast
            try:
                message = messaging.MulticastMessage(
                    notification=messaging.Notification(title=payload.title, body=payload.body) if not payload.silent else None,
                    data={k: str(v) for k, v in (payload.data or {}).items()},
                    tokens=tokens
                )
                response = messaging.send_multicast(message)
                # remove invalid tokens (best-effort)
                if response.failure_count > 0:
                    invalid_indexes = [i for i, resp in enumerate(response.responses) if not resp.success]
                    for idx in invalid_indexes:
                        token = tokens[idx]
                        try:
                            db.collection('device_tokens').document(token).delete()
                        except Exception:
                            pass
                return {'ok': True, 'fcm': {'success': response.success_count, 'failure': response.failure_count}, 'notification_id': nref.id}
            except Exception as e:
                logging.exception('FCM send error for %s: %s', student_id, e)
                return {'ok': False, 'error': 'Failed to send push', 'notification_id': nref.id}
        else:
            return {'ok': True, 'message': 'No device tokens registered', 'notification_id': nref.id}
    except Exception as e:
        logging.exception('Error sending notification to %s: %s', student_id, e)
        return {'ok': False, 'error': str(e)}


@router.post('/students', summary='Créer un étudiant avec Auth')
async def create_student(student: StudentCreate, current_user: Any = Depends(get_current_active_user)):
    """
    Crée un étudiant dans Auth, users et students.
    """
    db = firestore.client()
    # 1. Créer l'utilisateur dans Firebase Auth
    password = student.password or generate_random_password()
    try:
        user_record = auth.create_user(
            email=student.email,
            password=password,
            display_name=f"{student.first_name or ''} {student.last_name or ''}".strip(),
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail=f"L'email '{student.email}' est déjà utilisé par un autre compte.")
    # 2. Créer le profil dans users
    user_profile_data = {
        "firebase_uid": user_record.uid,
        "email": student.email,
        "display_name": f"{student.first_name or ''} {student.last_name or ''}".strip(),
        "first_name": student.first_name,
        "last_name": student.last_name,
        "role": "student",
        "created_at": firestore.SERVER_TIMESTAMP,
        "is_active": True,
    }
    db.collection("users").document(user_record.uid).set(user_profile_data, merge=True)
    # 3. Créer le document dans students
    student_data = student.model_dump(exclude_unset=True)
    student_data["auth_uid"] = user_record.uid
    student_data["created_at"] = firestore.SERVER_TIMESTAMP
    student_data["updated_at"] = firestore.SERVER_TIMESTAMP
    db.collection("students").document(user_record.uid).set(student_data, merge=True)
    return {"ok": True, "uid": user_record.uid, "email": user_record.email, "generated_password": password if student.password is None else None}


@router.put('/students/{student_id}', summary='Mettre à jour un étudiant avec Auth')
async def update_student(
    student_id: str = Path(..., description='UID Firebase ou ID étudiant'),
    student: StudentUpdate = Body(...),
    current_user: Any = Depends(get_current_active_user)
):
    db = firestore.client()
    # 1. Mettre à jour Firebase Auth
    auth_updates = {}
    if student.email:
        auth_updates['email'] = student.email
    if student.first_name or student.last_name:
        full_name = f"{student.first_name or ''} {student.last_name or ''}".strip()
        auth_updates['display_name'] = full_name
    if student.password:
        auth_updates['password'] = student.password
    if auth_updates:
        try:
            auth.update_user(student_id, **auth_updates)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f'Erreur mise à jour Auth: {e}')
    # 2. Mettre à jour users
    user_ref = db.collection('users').document(student_id)
    user_updates = student.model_dump(exclude_unset=True)
    if 'password' in user_updates:
        user_updates.pop('password')
    user_updates['updated_at'] = firestore.SERVER_TIMESTAMP
    user_ref.set(user_updates, merge=True)
    # 3. Mettre à jour students
    student_ref = db.collection('students').document(student_id)
    student_updates = student.model_dump(exclude_unset=True)
    if 'password' in student_updates:
        student_updates.pop('password')
    student_updates['updated_at'] = firestore.SERVER_TIMESTAMP
    student_ref.set(student_updates, merge=True)
    return {"ok": True, "student_id": student_id}
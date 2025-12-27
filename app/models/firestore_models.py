"""
Pydantic models and lightweight Firestore helpers.
These are thin wrappers to map Firestore documents <-> Pydantic models
and provide simple CRUD helpers used by the rest of the codebase.
"""
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar("T", bound="FirestoreModel")


class FirestoreModel(BaseModel):
    id: Optional[str] = Field(None, alias="id")

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

    @classmethod
    def from_doc(cls: Type[T], doc: Any) -> Optional[T]:
        if doc is None:
            return None
        if hasattr(doc, "to_dict"):
            data = doc.to_dict()
            data["id"] = getattr(doc, "id", None)
        elif isinstance(doc, dict):
            data = dict(doc)
        else:
            return None
        return cls.parse_obj(data)

    def to_dict(self) -> Dict[str, Any]:
        d = self.dict(by_alias=True, exclude_none=True)
        # remove `id` when writing into Firestore (use document id instead)
        d.pop("id", None)
        return d


# --- Core models (minimal fields for admin workflows) ---
class UniversityConfig(FirestoreModel):
    name: str
    logo_url: Optional[str] = None
    currency: Optional[str] = None
    address: Optional[str] = None
    contacts: Optional[Dict[str, Any]] = None
    lmd_params: Optional[Dict[str, Any]] = None
    active_academic_year_id: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class Faculty(FirestoreModel):
    university_id: Optional[str]
    name: str
    code: Optional[str]
    dean_user_id: Optional[str]
    secretary_user_id: Optional[str]
    finance_params: Optional[Dict[str, Any]]
    is_active: Optional[bool] = True
    is_deleted: Optional[bool] = False


class Department(FirestoreModel):
    faculty_id: Optional[str]
    name: str
    code: Optional[str]
    head_user_id: Optional[str]
    is_active: Optional[bool] = True


class Program(FirestoreModel):
    name: str
    cycle: Optional[str]
    department_id: Optional[str]
    credits_per_year: Optional[int]
    lmd_rules: Optional[Dict[str, Any]]
    is_active: Optional[bool] = True


class AcademicYear(FirestoreModel):
    name: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    is_active: Optional[bool] = False


class Promotion(FirestoreModel):
    name: str
    level: Optional[str]
    academic_year_id: Optional[str]
    program_id: Optional[str]
    status: Optional[str]
    archived: Optional[bool] = False


class User(FirestoreModel):
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = "student"
    is_active: Optional[bool] = True


class Student(FirestoreModel):
    matricule: Optional[str]
    firstname: str
    lastname: str
    dob: Optional[datetime]
    email: Optional[str]
    status: Optional[str] = "active"
    program_id: Optional[str]
    promotion_id: Optional[str]
    financial_account: Optional[Dict[str, Any]]


class Teacher(FirestoreModel):
    user_id: Optional[str]
    grade: Optional[str]
    contract: Optional[Dict[str, Any]]
    workload: Optional[int]


class UE(FirestoreModel):
    code: Optional[str]
    title: str
    credits: Optional[int]
    semester: Optional[str]
    cycle: Optional[str]
    prerequisites: Optional[Dict[str, Any]]
    version: Optional[int] = 1
    is_active: Optional[bool] = True


class Enrollment(FirestoreModel):
    student_id: str
    ue_id: str
    session: Optional[str]
    status: Optional[str] = "enrolled"
    grades: Optional[Dict[str, Any]]


class Grade(FirestoreModel):
    enrollment_id: str
    assessment_type: Optional[str]
    value: Optional[float]
    weight: Optional[float]


class Payment(FirestoreModel):
    student_id: str
    amount: float
    date: Optional[datetime]
    type: Optional[str]
    receipt_no: Optional[str]
    status: Optional[str]


class AuditLog(FirestoreModel):
    user_id: Optional[str]
    action: str
    object_type: Optional[str]
    object_id: Optional[str]
    details: Optional[Dict[str, Any]]
    timestamp: Optional[datetime]


# --- Firestore helpers ---
try:
    from firebase_admin import firestore
except Exception:  # pragma: no cover - allows importing without firebase during tests
    firestore = None


def _get_client():
    if firestore is None:
        raise RuntimeError("firebase_admin.firestore is not available. Initialize Firebase before using these helpers.")
    return firestore.client()


def create_doc(collection: str, data: Dict[str, Any]) -> str:
    db = _get_client()
    ref = db.collection(collection).document()
    ref.set(data)
    return ref.id


def get_doc(collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
    db = _get_client()
    ref = db.collection(collection).document(str(doc_id))
    doc = ref.get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    d["id"] = doc.id
    return d


def update_doc(collection: str, doc_id: str, data: Dict[str, Any]) -> None:
    db = _get_client()
    ref = db.collection(collection).document(str(doc_id))
    ref.update(data)


def delete_doc(collection: str, doc_id: str) -> None:
    db = _get_client()
    ref = db.collection(collection).document(str(doc_id))
    ref.delete()


def list_docs(collection: str, where: Optional[List[tuple]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    db = _get_client()
    q = db.collection(collection)
    if where:
        for w in where:
            if len(w) == 3:
                field, op, value = w
                q = q.where(field, op, value)
    if limit:
        docs = q.limit(limit).stream()
    else:
        docs = q.stream()
    out = []
    for d in docs:
        dd = d.to_dict()
        dd["id"] = d.id
        out.append(dd)
    return out


# Small utility to convert a Firestore doc dict to a model instance
def doc_to_model(model_cls: Type[T], doc: Dict[str, Any]) -> T:
    return model_cls.parse_obj(doc)


__all__ = [
    "FirestoreModel",
    "UniversityConfig",
    "Faculty",
    "Department",
    "Program",
    "AcademicYear",
    "Promotion",
    "User",
    "Student",
    "Teacher",
    "UE",
    "Enrollment",
    "Grade",
    "Payment",
    "AuditLog",
    "create_doc",
    "get_doc",
    "update_doc",
    "delete_doc",
    "list_docs",
    "doc_to_model",
]

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

class FacultyCreate(BaseModel):
    university_id: Optional[str] = None
    name: str
    code: Optional[str] = None
    dean_user_id: Optional[str] = None
    secretary_user_id: Optional[str] = None
    finance_params: Optional[Dict[str, Any]] = None

class FacultyOut(FacultyCreate):
    id: str
    is_active: Optional[bool] = True
    is_deleted: Optional[bool] = False

class UniversityConfigSchema(BaseModel):
    id: Optional[str]
    name: str
    logo_url: Optional[str]
    currency: Optional[str]
    address: Optional[str]
    contacts: Optional[Dict[str, Any]]
    lmd_params: Optional[Dict[str, Any]]
    active_academic_year_id: Optional[str]
    settings: Optional[Dict[str, Any]]
    updated_by: Optional[str]
    updated_at: Optional[datetime]

class FacultyListResponse(BaseModel):
    total: int
    faculties: List[FacultyOut]

class DepartmentCreate(BaseModel):
    faculty_id: Optional[str] = None
    name: str
    code: Optional[str] = None
    head_user_id: Optional[str] = None
    is_active: Optional[bool] = True
    is_deleted: Optional[bool] = False

class DepartmentOut(DepartmentCreate):
    id: Optional[str]

class ProgramCreate(BaseModel):
    faculty_id: Optional[str] = None
    department_id: Optional[str] = None
    name: str
    code: Optional[str] = None
    level: Optional[str] = None
    duration_years: Optional[int] = None
    is_active: Optional[bool] = True
    is_deleted: Optional[bool] = False

class ProgramOut(ProgramCreate):
    id: Optional[str]

class PromotionCreate(BaseModel):
    program_id: Optional[str] = None
    name: str
    year: Optional[int] = None
    is_active: Optional[bool] = True
    is_deleted: Optional[bool] = False

class PromotionOut(PromotionCreate):
    id: Optional[str]

class EnrollmentCreate(BaseModel):
    student_id: str
    promotion_id: Optional[str]
    group_id: Optional[str]
    academic_year_id: Optional[str]
    status: Optional[str] = 'enrolled'  # enrolled, cancelled, transferred

class EnrollmentOut(EnrollmentCreate):
    id: Optional[str]

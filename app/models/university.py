"""
Modèles : Structure universitaire (Université → Faculté → Département → Option)
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON, Boolean, DateTime
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class University(BaseModel):
    """Université"""
    __tablename__ = "universities"
    
    name = Column(String(255), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    acronym = Column(String(20), nullable=True)
    logo_url = Column(String(500), nullable=True)
    address = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Paramètres LMD par défaut
    lmd_settings = Column(JSON, nullable=True)
    
    # Relations
    faculties = relationship("Faculty", back_populates="university", cascade="all, delete-orphan")


class Faculty(BaseModel):
    """Faculté (modèle duplicable)"""
    __tablename__ = "faculties"
    
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    acronym = Column(String(20), nullable=True)
    dean_name = Column(String(255), nullable=True)
    vice_dean_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    
    # Cycles actifs dans cette faculté
    has_graduat = Column(Boolean, default=True)
    has_licence = Column(Boolean, default=False)
    has_master = Column(Boolean, default=False)
    has_doctorat = Column(Boolean, default=False)
    
    # Paramètres LMD spécifiques (peut surcharger université)
    lmd_settings = Column(JSON, nullable=True)
    
    # Relations
    university = relationship("University", back_populates="faculties")
    departments = relationship("Department", back_populates="faculty", cascade="all, delete-orphan")
    financial_settings = relationship("FacultyFinancialSettings", back_populates="faculty", uselist=False)


class Department(BaseModel):
    """Département (au sein d'une faculté)"""
    __tablename__ = "departments"
    
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    head_name = Column(String(255), nullable=True)
    secretary_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Relations
    faculty = relationship("Faculty", back_populates="departments")
    options = relationship("Option", back_populates="department", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="department")


class Option(BaseModel):
    """Option / Filière (au sein d'un département)"""
    __tablename__ = "options"
    
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    
    # Cycles disponibles pour cette option
    has_graduat = Column(Boolean, default=True)
    has_licence = Column(Boolean, default=False)
    has_master = Column(Boolean, default=False)
    
    # Relations
    department = relationship("Department", back_populates="options")
    promotions = relationship("Promotion", back_populates="option", cascade="all, delete-orphan")


class AcademicYear(BaseModel):
    """Année académique"""
    __tablename__ = "academic_years"
    
    name = Column(String(50), nullable=False, unique=True)  # Ex: "2023-2024"
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_current = Column(Boolean, default=False)
    is_closed = Column(Boolean, default=False)
    
    # Relations
    sessions = relationship("Session", back_populates="academic_year", cascade="all, delete-orphan")


class Session(BaseModel):
    """Session (1ère, 2e, spéciale)"""
    __tablename__ = "sessions"
    
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    
    name = Column(String(50), nullable=False)  # "1ère session", "2e session"
    session_type = Column(String(20), nullable=False)  # "first", "second", "special"
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_closed = Column(Boolean, default=False)
    
    # Relations
    academic_year = relationship("AcademicYear", back_populates="sessions")
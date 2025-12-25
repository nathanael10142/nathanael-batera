"""
Modèles : Étudiants et leur parcours académique
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Date, Float, Text, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class CycleType(str, enum.Enum):
    """Types de cycles"""
    GRADUAT = "graduat"
    LICENCE = "licence"
    MASTER = "master"
    DOCTORAT = "doctorat"


class YearLevel(str, enum.Enum):
    """Niveaux d'année"""
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"
    M1 = "M1"
    M2 = "M2"
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"


class StudentStatus(str, enum.Enum):
    """Statut étudiant"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    GRADUATED = "graduated"
    DROPPED_OUT = "dropped_out"
    REORIENTED = "reoriented"


class Promotion(BaseModel):
    """Promotion (année + option + cycle)"""
    __tablename__ = "promotions"
    
    option_id = Column(Integer, ForeignKey("options.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    
    cycle = Column(SQLEnum(CycleType), nullable=False)
    year_level = Column(SQLEnum(YearLevel), nullable=False)
    name = Column(String(255), nullable=False)  # Ex: "L1 Info 2023-2024"
    
    # Relations
    option = relationship("Option", back_populates="promotions")
    academic_year = relationship("AcademicYear")
    classes = relationship("Class", back_populates="promotion", cascade="all, delete-orphan")
    students = relationship("Student", back_populates="promotion")


class Class(BaseModel):
    """Classe / Groupe (subdivision d'une promotion)"""
    __tablename__ = "classes"
    
    promotion_id = Column(Integer, ForeignKey("promotions.id"), nullable=False)
    
    name = Column(String(100), nullable=False)  # Ex: "Groupe A"
    capacity = Column(Integer, default=50)
    
    # Relations
    promotion = relationship("Promotion", back_populates="classes")
    students = relationship("Student", back_populates="class_group")


class Student(BaseModel):
    """Étudiant"""
    __tablename__ = "students"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    promotion_id = Column(Integer, ForeignKey("promotions.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    
    # Informations personnelles
    matricule = Column(String(50), nullable=False, unique=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    date_of_birth = Column(Date, nullable=False)
    place_of_birth = Column(String(255), nullable=True)
    gender = Column(String(10), nullable=False)
    
    # Contact
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    
    # Urgence
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(50), nullable=True)
    
    # Photo
    photo_url = Column(String(500), nullable=True)
    
    # Statut académique
    status = Column(SQLEnum(StudentStatus), default=StudentStatus.ACTIVE)
    enrollment_date = Column(Date, nullable=False)
    graduation_date = Column(Date, nullable=True)
    
    # Statut financier
    financial_blocked = Column(Boolean, default=False)
    
    # Relations
    user = relationship("User", back_populates="student_profile")
    promotion = relationship("Promotion", back_populates="students")
    class_group = relationship("Class", back_populates="students")
    enrollments = relationship("CourseEnrollment", back_populates="student")
    grades = relationship("Grade", back_populates="student")
    academic_records = relationship("AcademicRecord", back_populates="student")
    payments = relationship("Payment", back_populates="student")


class AcademicRecord(BaseModel):
    """Dossier académique étudiant (par année)"""
    __tablename__ = "academic_records"
    
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    
    # Crédits
    total_credits_attempted = Column(Integer, default=0)
    total_credits_earned = Column(Integer, default=0)
    credits_in_debt = Column(Integer, default=0)
    
    # Moyennes
    gpa_first_session = Column(Float, nullable=True)
    gpa_second_session = Column(Float, nullable=True)
    gpa_final = Column(Float, nullable=True)
    
    # Décisions académiques
    decision = Column(String(50), nullable=True)  # "admis", "ajourné", "redoublant"
    is_conditional = Column(Boolean, default=False)
    can_progress = Column(Boolean, default=False)
    
    # Détails LMD
    lmd_data = Column(JSON, nullable=True)  # Stockage flexible pour données LMD
    
    # Relations
    student = relationship("Student", back_populates="academic_records")
    academic_year = relationship("AcademicYear")
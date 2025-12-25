"""
Modèles : Cours (UE) et gestion académique
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Float, Text, JSON, Boolean, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class CourseType(str, enum.Enum):
    """Type de cours"""
    MANDATORY = "mandatory"  # Obligatoire
    OPTIONAL = "optional"    # Optionnel


class Semester(str, enum.Enum):
    """Semestre"""
    FIRST = "first"
    SECOND = "second"


class Course(BaseModel):
    """Unité d'Enseignement (UE)"""
    __tablename__ = "courses"
    
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Crédits et volume horaire
    credits = Column(Integer, nullable=False)
    theory_hours = Column(Integer, default=0)
    practical_hours = Column(Integer, default=0)
    total_hours = Column(Integer, nullable=False)
    
    # Type et niveau
    course_type = Column(SQLEnum(CourseType), default=CourseType.MANDATORY)
    semester = Column(SQLEnum(Semester), nullable=False)
    cycle = Column(String(20), nullable=False)  # graduat, licence, master
    year_level = Column(String(10), nullable=False)  # L1, L2, M1, etc.
    
    # Prérequis (liste de codes de cours)
    prerequisites = Column(JSON, nullable=True)  # ["MATH101", "PHYS101"]
    
    # Relations
    department = relationship("Department", back_populates="courses")
    course_assignments = relationship("CourseAssignment", back_populates="course")
    enrollments = relationship("CourseEnrollment", back_populates="course")
    grades = relationship("Grade", back_populates="course")


class CourseAssignment(BaseModel):
    """Attribution de cours à un enseignant"""
    __tablename__ = "course_assignments"
    
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    promotion_id = Column(Integer, ForeignKey("promotions.id"), nullable=False)
    
    # Type d'enseignement
    assignment_type = Column(String(50), default="theory")  # theory, practical, both
    
    # Relations
    course = relationship("Course", back_populates="course_assignments")
    teacher = relationship("Teacher", back_populates="course_assignments")
    academic_year = relationship("AcademicYear")
    promotion = relationship("Promotion")


class CourseEnrollment(BaseModel):
    """Inscription d'un étudiant à un cours"""
    __tablename__ = "course_enrollments"
    
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    
    is_retake = Column(Boolean, default=False)  # Reprise
    
    # Relations
    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    academic_year = relationship("AcademicYear")
    session = relationship("Session")


class Grade(BaseModel):
    """Note d'un étudiant"""
    __tablename__ = "grades"
    
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    
    # Notes
    exam_score = Column(Float, nullable=True)
    continuous_assessment = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    
    # Statut
    is_validated = Column(Boolean, default=False)
    validated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    
    # Résultat
    credits_earned = Column(Integer, default=0)
    is_passed = Column(Boolean, default=False)
    is_capitalized = Column(Boolean, default=False)  # Capitalisé
    is_compensated = Column(Boolean, default=False)  # Compensé
    
    # Historique des modifications
    modification_history = Column(JSON, nullable=True)
    
    # Relations
    student = relationship("Student", back_populates="grades")
    course = relationship("Course", back_populates="grades")
    academic_year = relationship("AcademicYear")
    session = relationship("Session")
    teacher = relationship("Teacher", foreign_keys=[teacher_id])
    validator = relationship("User", foreign_keys=[validated_by])


class Teacher(BaseModel):
    """Enseignant"""
    __tablename__ = "teachers"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    
    # Informations personnelles
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    title = Column(String(50), nullable=True)  # Prof, Dr, Ass, CT
    specialization = Column(String(255), nullable=True)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(50), nullable=True)
    photo_url = Column(String(500), nullable=True)
    
    # Statut
    employment_type = Column(String(50), nullable=True)  # permanent, contractual, visiting
    
    # Relations
    user = relationship("User", back_populates="teacher_profile")
    department = relationship("Department")
    course_assignments = relationship("CourseAssignment", back_populates="teacher")
    grades = relationship("Grade", foreign_keys="Grade.teacher_id")
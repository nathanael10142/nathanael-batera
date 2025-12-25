"""
Import tous les modèles pour Alembic
"""
from app.models.base import Base, BaseModel
from app.models.university import University, Faculty, Department, Option, AcademicYear, Session
from app.models.student import (
    Promotion, Class, Student, AcademicRecord,
    CycleType, YearLevel, StudentStatus
)
from app.models.course import (
    Course, CourseAssignment, CourseEnrollment, Grade, Teacher,
    CourseType, Semester
)
from app.models.user import User, Role, Permission, role_permissions
from app.models.financial import (
    FacultyFinancialSettings, FeeStructure, Payment, AccountingEntry, FinancialReport,
    PaymentMethod, PaymentStatus, FeeType
)
from app.models.communication import (
    Conversation, ConversationParticipant, Message, MessageReadReceipt, Notification,
    MessageType, ConversationType
)
from app.models.audit import AuditLog, SystemLog


__all__ = [
    "Base",
    "BaseModel",
    # University structure
    "University",
    "Faculty",
    "Department",
    "Option",
    "AcademicYear",
    "Session",
    # Students
    "Promotion",
    "Class",
    "Student",
    "AcademicRecord",
    "CycleType",
    "YearLevel",
    "StudentStatus",
    # Courses
    "Course",
    "CourseAssignment",
    "CourseEnrollment",
    "Grade",
    "Teacher",
    "CourseType",
    "Semester",
    # Users
    "User",
    "Role",
    "Permission",
    "role_permissions",
    # Financial
    "FacultyFinancialSettings",
    "FeeStructure",
    "Payment",
    "AccountingEntry",
    "FinancialReport",
    "PaymentMethod",
    "PaymentStatus",
    "FeeType",
    # Communication
    "Conversation",
    "ConversationParticipant",
    "Message",
    "MessageReadReceipt",
    "Notification",
    "MessageType",
    "ConversationType",
    # Audit
    "AuditLog",
    "SystemLog",
]
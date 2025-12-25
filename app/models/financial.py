"""
Modèles : Gestion financière et comptabilité
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Float, Text, JSON, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.models.base import BaseModel


class PaymentMethod(str, enum.Enum):
    """Méthode de paiement"""
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_MONEY = "mobile_money"
    CHEQUE = "cheque"


class PaymentStatus(str, enum.Enum):
    """Statut du paiement"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class FeeType(str, enum.Enum):
    """Type de frais"""
    INSCRIPTION = "inscription"
    MINERVAL = "minerval"
    LIBRARY = "library"
    SPORTS = "sports"
    INSURANCE = "insurance"
    EXAM = "exam"
    OTHER = "other"


class FacultyFinancialSettings(BaseModel):
    """Paramètres financiers d'une faculté"""
    __tablename__ = "faculty_financial_settings"
    
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=False, unique=True)
    
    # Compte bancaire facultaire
    bank_account_number = Column(String(100), nullable=True)
    bank_name = Column(String(255), nullable=True)
    
    # Mobile Money
    mobile_money_number = Column(String(50), nullable=True)
    mobile_money_provider = Column(String(50), nullable=True)
    
    # Paramètres comptables
    accounting_code_prefix = Column(String(20), nullable=True)
    
    # Relations
    faculty = relationship("Faculty", back_populates="financial_settings")


class FeeStructure(BaseModel):
    """Structure de frais (par faculté, cycle, année)"""
    __tablename__ = "fee_structures"
    
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    
    cycle = Column(String(20), nullable=False)  # graduat, licence, master
    year_level = Column(String(10), nullable=False)  # L1, L2, M1, etc.
    
    fee_type = Column(SQLEnum(FeeType), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    
    description = Column(Text, nullable=True)
    is_mandatory = Column(Boolean, default=True)
    due_date = Column(DateTime, nullable=True)
    
    # Relations
    faculty = relationship("Faculty")
    academic_year = relationship("AcademicYear")


class Payment(BaseModel):
    """Paiement étudiant"""
    __tablename__ = "payments"
    
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    
    # Détails du paiement
    reference_number = Column(String(100), nullable=False, unique=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    
    fee_type = Column(SQLEnum(FeeType), nullable=False)
    
    # Dates
    payment_date = Column(DateTime, default=datetime.utcnow)
    processed_date = Column(DateTime, nullable=True)
    
    # Détails spécifiques au mode de paiement
    payment_details = Column(JSON, nullable=True)  # Transaction ID, phone, etc.
    
    # Traitement
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Reçu
    receipt_url = Column(String(500), nullable=True)
    
    # Relations
    student = relationship("Student", back_populates="payments")
    academic_year = relationship("AcademicYear")
    processor = relationship("User")


class AccountingEntry(BaseModel):
    """Écriture comptable"""
    __tablename__ = "accounting_entries"
    
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    
    # Écriture
    entry_date = Column(DateTime, default=datetime.utcnow)
    reference = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    
    # Compte
    account_code = Column(String(50), nullable=False)
    account_name = Column(String(255), nullable=False)
    
    # Montants
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    
    # Devise
    currency = Column(String(10), default="USD")
    
    # Lien avec paiement
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    
    # Validation
    is_validated = Column(Boolean, default=False)
    validated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    
    # Relations
    faculty = relationship("Faculty")
    academic_year = relationship("AcademicYear")
    payment = relationship("Payment")
    validator = relationship("User", foreign_keys=[validated_by])


class FinancialReport(BaseModel):
    """Rapport financier"""
    __tablename__ = "financial_reports"
    
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    
    report_type = Column(String(50), nullable=False)  # balance, journal, ledger
    report_period = Column(String(50), nullable=False)  # monthly, quarterly, annual
    
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Données du rapport
    report_data = Column(JSON, nullable=True)
    
    # Fichier généré
    report_file_url = Column(String(500), nullable=True)
    
    # Génération
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    faculty = relationship("Faculty")
    academic_year = relationship("AcademicYear")
    generator = relationship("User")
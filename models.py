from sqlalchemy import (
    Column, Integer, String, DateTime, func, Boolean, Float, Text,
    ForeignKey, Table, Enum as SQLAlchemyEnum, Date
)
from sqlalchemy.orm import relationship
from database import Base
import enum

# --- Enums pour les choix fixes ---
class CycleType(enum.Enum):
    GRADUAT = "Graduat"
    LICENCE = "Licence"
    MASTER = "Master"
    DOCTORAT = "Doctorat"

class StatutAcademique(enum.Enum):
    INSCRIT = "Inscrit"
    BLOQUE = "Bloqué"
    GRADUE = "Gradué"

class StatutFinancier(enum.Enum):
    OK = "OK"
    BLOQUE = "Bloqué"

class TypeUE(enum.Enum):
    OBLIGATOIRE = "Obligatoire"
    OPTIONNELLE = "Optionnelle"

class StatutUE(enum.Enum):
    VALIDE = "Validé"
    DETTES = "Dettes"
    REDOUBLE = "Redouble"

class ModePaiement(enum.Enum):
    MOBILE_MONEY = "Mobile Money"
    BANQUE = "Banque"

class StatutPaiement(enum.Enum):
    VALIDE = "Validé"
    EN_ATTENTE = "En attente"

class TypeDocument(enum.Enum):
    BULLETIN = "Bulletin"
    ATTESTATION = "Attestation"
    DIPLOME = "Diplôme"

# Mixin pour les timestamps
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 1. Universite
class Universite(Base, TimestampMixin):
    __tablename__ = "universite"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    facultes = relationship("Faculte", back_populates="universite")

# 2. Faculte
class Faculte(Base, TimestampMixin):
    __tablename__ = "faculte"
    id = Column(Integer, primary_key=True, index=True)
    universite_id = Column(Integer, ForeignKey('universite.id'), nullable=False)
    nom = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    universite = relationship("Universite", back_populates="facultes")
    departements = relationship("Departement", back_populates="faculte")
    paiements = relationship("Paiement", back_populates="faculte")

# 3. Departement
class Departement(Base, TimestampMixin):
    __tablename__ = "departement"
    id = Column(Integer, primary_key=True, index=True)
    faculte_id = Column(Integer, ForeignKey('faculte.id'), nullable=False)
    nom = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    faculte = relationship("Faculte", back_populates="departements")
    options = relationship("OptionFiliere", back_populates="departement")
    enseignants = relationship("Enseignant", back_populates="departement")
    ues = relationship("UE", back_populates="departement")

# 4. Option / Filiere
class OptionFiliere(Base, TimestampMixin):
    __tablename__ = "option_filiere"
    id = Column(Integer, primary_key=True, index=True)
    departement_id = Column(Integer, ForeignKey('departement.id'), nullable=False)
    nom = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    cycle = Column(SQLAlchemyEnum(CycleType), nullable=False)
    departement = relationship("Departement", back_populates="options")
    promotions = relationship("Promotion", back_populates="option")

# 5. Promotion
class Promotion(Base, TimestampMixin):
    __tablename__ = "promotion"
    id = Column(Integer, primary_key=True, index=True)
    option_id = Column(Integer, ForeignKey('option_filiere.id'), nullable=False)
    annee_academique = Column(String(9), nullable=False) # ex: 2025-2026
    niveau = Column(String(10), nullable=False) # L1, L2, M1...
    option = relationship("OptionFiliere", back_populates="promotions")
    groupes = relationship("Groupe", back_populates="promotion")

# 6. Groupe
class Groupe(Base, TimestampMixin):
    __tablename__ = "groupe"
    id = Column(Integer, primary_key=True, index=True)
    promotion_id = Column(Integer, ForeignKey('promotion.id'), nullable=False)
    nom = Column(String(50), nullable=False) # G1, G2
    promotion = relationship("Promotion", back_populates="groupes")
    etudiants = relationship("Etudiant", back_populates="groupe")

# 7. Etudiant
class Etudiant(Base, TimestampMixin):
    __tablename__ = "etudiant"
    id = Column(Integer, primary_key=True, index=True)
    groupe_id = Column(Integer, ForeignKey('groupe.id'), nullable=False)
    matricule = Column(String(50), unique=True, nullable=False)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    date_naissance = Column(Date)
    email = Column(String(255))
    telephone = Column(String(50))
    statut_academique = Column(SQLAlchemyEnum(StatutAcademique), default=StatutAcademique.INSCRIT)
    statut_financier = Column(SQLAlchemyEnum(StatutFinancier), default=StatutFinancier.OK)
    groupe = relationship("Groupe", back_populates="etudiants")
    utilisateur = relationship("Utilisateur", back_populates="etudiant", uselist=False)
    notes = relationship("EtudiantUE", back_populates="etudiant")
    paiements = relationship("Paiement", back_populates="etudiant")
    documents = relationship("Document", back_populates="etudiant")

# 8. Enseignant
class Enseignant(Base, TimestampMixin):
    __tablename__ = "enseignant"
    id = Column(Integer, primary_key=True, index=True)
    departement_id = Column(Integer, ForeignKey('departement.id'), nullable=False)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(255))
    telephone = Column(String(50))
    role = Column(String(100)) # Assistant, CT, Professeur
    departement = relationship("Departement", back_populates="enseignants")
    utilisateur = relationship("Utilisateur", back_populates="enseignant", uselist=False)

# 9. UE (Unité d'Enseignement)
class UE(Base, TimestampMixin):
    __tablename__ = "ue"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), nullable=False)
    intitule = Column(String(255), nullable=False)
    credits = Column(Integer, nullable=False)
    volume_horaire = Column(Integer)
    type_ue = Column(SQLAlchemyEnum(TypeUE), default=TypeUE.OBLIGATOIRE)
    prerequis = Column(Text)
    semestre = Column(Integer)
    cycle = Column(SQLAlchemyEnum(CycleType))
    departement_id = Column(Integer, ForeignKey('departement.id'))
    departement = relationship("Departement", back_populates="ues")
    notes = relationship("EtudiantUE", back_populates="ue")

# 10. EtudiantUE (Notes)
class EtudiantUE(Base, TimestampMixin):
    __tablename__ = "etudiant_ue"
    id = Column(Integer, primary_key=True, index=True)
    etudiant_id = Column(Integer, ForeignKey('etudiant.id'), nullable=False)
    ue_id = Column(Integer, ForeignKey('ue.id'), nullable=False)
    session = Column(String(50)) # 1ère session, 2e session
    note = Column(Float)
    statut = Column(SQLAlchemyEnum(StatutUE))
    etudiant = relationship("Etudiant", back_populates="notes")
    ue = relationship("UE", back_populates="notes")

# 11. Paiement
class Paiement(Base, TimestampMixin):
    __tablename__ = "paiement"
    id = Column(Integer, primary_key=True, index=True)
    etudiant_id = Column(Integer, ForeignKey('etudiant.id'), nullable=False)
    faculte_id = Column(Integer, ForeignKey('faculte.id'), nullable=False)
    montant = Column(Float, nullable=False)
    mode_paiement = Column(SQLAlchemyEnum(ModePaiement))
    date_paiement = Column(DateTime)
    statut = Column(SQLAlchemyEnum(StatutPaiement), default=StatutPaiement.EN_ATTENTE)
    recu_num = Column(String(100), unique=True)
    etudiant = relationship("Etudiant", back_populates="paiements")
    faculte = relationship("Faculte", back_populates="paiements")

# 12. Role
class Role(Base):
    __tablename__ = "role"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), unique=True, nullable=False)
    utilisateurs = relationship("Utilisateur", back_populates="role")

# 13. Utilisateur
class Utilisateur(Base, TimestampMixin):
    __tablename__ = "utilisateur"
    id = Column(Integer, primary_key=True, index=True)
    etudiant_id = Column(Integer, ForeignKey('etudiant.id'), nullable=True)
    enseignant_id = Column(Integer, ForeignKey('enseignant.id'), nullable=True)
    nom_utilisateur = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    mot_de_passe = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey('role.id'))
    actif = Column(Boolean, default=True)
    
    role = relationship("Role", back_populates="utilisateurs")
    etudiant = relationship("Etudiant", back_populates="utilisateur")
    enseignant = relationship("Enseignant", back_populates="utilisateur")

# 14. Document
class Document(Base):
    __tablename__ = "document"
    id = Column(Integer, primary_key=True, index=True)
    etudiant_id = Column(Integer, ForeignKey('etudiant.id'), nullable=False)
    type_document = Column(SQLAlchemyEnum(TypeDocument))
    fichier = Column(String(255))
    date_emission = Column(Date)
    validite = Column(Date)
    etudiant = relationship("Etudiant", back_populates="documents")

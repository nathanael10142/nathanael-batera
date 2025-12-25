"""
Modèles : Utilisateurs, rôles et permissions
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Table
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


# Table d'association roles-permissions (many-to-many)
role_permissions = Table(
    'role_permissions',
    BaseModel.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)


class User(BaseModel):
    """Utilisateur du système"""
    __tablename__ = "users"
    
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Statut
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    
    # Rôle
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    
    # Faculté (pour isolation multi-tenant)
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=True)
    
    # Relations
    role = relationship("Role", back_populates="users")
    faculty = relationship("Faculty")
    student_profile = relationship("Student", back_populates="user", uselist=False)
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")


class Role(BaseModel):
    """Rôle utilisateur"""
    __tablename__ = "roles"
    
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Catégorie
    category = Column(String(50), nullable=True)  # academic, administrative, financial
    
    # Niveau hiérarchique
    hierarchy_level = Column(Integer, default=0)
    
    # Relations
    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(BaseModel):
    """Permission"""
    __tablename__ = "permissions"
    
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    
    # Relations
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
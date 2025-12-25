# Original SQLAlchemy models archived here for reference.
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Table, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


role_permissions = Table(
    'role_permissions',
    BaseModel.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)


class User(BaseModel):
    __tablename__ = "users"
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)


class Role(BaseModel):
    __tablename__ = "roles"
    name = Column(String(100), nullable=False, unique=True)


class Permission(BaseModel):
    __tablename__ = "permissions"
    name = Column(String(100), nullable=False, unique=True)
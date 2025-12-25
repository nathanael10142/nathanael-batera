"""
Modèles : Audit et traçabilité
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel


class AuditLog(BaseModel):
    """Journal d'audit (immuable)"""
    __tablename__ = "audit_logs"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Action
    action = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # academic, financial, administrative
    description = Column(Text, nullable=False)
    
    # Contexte
    entity_type = Column(String(100), nullable=True)  # Student, Grade, Payment, etc.
    entity_id = Column(Integer, nullable=True)
    
    # Données
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    # Métadonnées
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relations
    user = relationship("User", back_populates="audit_logs")


class SystemLog(BaseModel):
    """Log système"""
    __tablename__ = "system_logs"
    
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    logger_name = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    
    # Contexte
    module = Column(String(100), nullable=True)
    function = Column(String(100), nullable=True)
    
    # Exception
    exception_type = Column(String(100), nullable=True)
    exception_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    
    # Métadonnées
    extra_data = Column(JSON, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
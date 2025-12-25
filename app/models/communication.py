"""
Modèles : Communication (messagerie type WhatsApp)
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Boolean, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.models.base import BaseModel


class MessageType(str, enum.Enum):
    """Type de message"""
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    DOCUMENT = "document"
    OFFICIAL = "official"  # Message officiel non supprimable


class ConversationType(str, enum.Enum):
    """Type de conversation"""
    DIRECT = "direct"  # 1-to-1
    GROUP = "group"    # Groupe (classe, promotion, département)
    OFFICIAL = "official"  # Canal officiel (administration)


class Conversation(BaseModel):
    """Conversation / Groupe"""
    __tablename__ = "conversations"
    
    conversation_type = Column(SQLEnum(ConversationType), nullable=False)
    name = Column(String(255), nullable=True)  # Nom du groupe
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Groupe automatique (lié à entité académique)
    is_auto_group = Column(Boolean, default=False)
    promotion_id = Column(Integer, ForeignKey("promotions.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    
    # Créateur
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relations
    creator = relationship("User", foreign_keys=[created_by])
    promotion = relationship("Promotion")
    class_group = relationship("Class")
    department = relationship("Department")
    participants = relationship("ConversationParticipant", back_populates="conversation")
    messages = relationship("Message", back_populates="conversation")


class ConversationParticipant(BaseModel):
    """Participant à une conversation"""
    __tablename__ = "conversation_participants"
    
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Rôle dans la conversation
    is_admin = Column(Boolean, default=False)
    
    # Notifications
    muted = Column(Boolean, default=False)
    
    # Lecture
    last_read_at = Column(DateTime, nullable=True)
    
    # Relations
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User")


class Message(BaseModel):
    """Message"""
    __tablename__ = "messages"
    
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Contenu
    message_type = Column(SQLEnum(MessageType), default=MessageType.TEXT)
    content = Column(Text, nullable=True)
    
    # Fichier attaché
    file_url = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(50), nullable=True)
    
    # Message officiel
    is_official = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    
    # Statut
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    
    # Réponse à un message
    reply_to_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    
    # Relations
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User")
    reply_to = relationship("Message", remote_side="Message.id")
    read_receipts = relationship("MessageReadReceipt", back_populates="message")


class MessageReadReceipt(BaseModel):
    """Accusé de lecture"""
    __tablename__ = "message_read_receipts"
    
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    read_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    message = relationship("Message", back_populates="read_receipts")
    user = relationship("User")


class Notification(BaseModel):
    """Notification push"""
    __tablename__ = "notifications"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Type de notification
    notification_type = Column(String(50), nullable=False)  # message, grade, payment, etc.
    
    # Contenu
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Données additionnelles
    
    # Lien
    link_url = Column(String(500), nullable=True)
    
    # Statut
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # Push mobile
    is_pushed = Column(Boolean, default=False)
    pushed_at = Column(DateTime, nullable=True)
    
    # Relations
    user = relationship("User")
"""
Modèles : Communication (messagerie type WhatsApp)
"""

# Lightweight placeholder for communication models in Firestore deployment.
from types import SimpleNamespace

class Conversation(SimpleNamespace):
    pass

class ConversationParticipant(SimpleNamespace):
    pass

class Message(SimpleNamespace):
    pass

class MessageReadReceipt(SimpleNamespace):
    pass

class Notification(SimpleNamespace):
    pass

__all__ = ["Conversation","ConversationParticipant","Message","MessageReadReceipt","Notification"]
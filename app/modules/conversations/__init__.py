"""
Conversations Module - Histórico de mensagens WhatsApp.
"""
from app.modules.conversations.models import Conversation, Message, MessageType, MessageDirection
from app.modules.conversations.schemas import (
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from app.modules.conversations.service import ConversationService

__all__ = [
    "Conversation",
    "Message",
    "MessageType",
    "MessageDirection",
    "ConversationResponse",
    "MessageCreate",
    "MessageResponse",
    "ConversationService",
]
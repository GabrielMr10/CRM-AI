"""
Schemas Pydantic para Conversations.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from app.modules.conversations.models import MessageType, MessageDirection, MessageStatus


# ==================== MESSAGE ====================

class MessageCreate(BaseModel):
    """Para enviar mensagem manual."""
    content: str = Field(..., min_length=1)
    message_type: MessageType = MessageType.TEXT


class MessageFromWebhook(BaseModel):
    """Mensagem recebida do webhook Z-API."""
    external_id: str
    phone: str
    content: str | None = None
    message_type: MessageType = MessageType.TEXT
    direction: MessageDirection
    media_url: str | None = None
    media_mime_type: str | None = None
    media_filename: str | None = None
    whatsapp_timestamp: datetime | None = None
    contact_name: str | None = None
    raw_data: dict = Field(default_factory=dict)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    external_id: str | None
    content: str | None
    message_type: str
    direction: str
    status: str
    media_url: str | None
    media_mime_type: str | None
    media_filename: str | None
    sent_by_id: uuid.UUID | None
    sent_by_bot: bool
    conversation_id: uuid.UUID
    created_at: datetime
    whatsapp_timestamp: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    has_more: bool


# ==================== CONVERSATION ====================

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    phone: str
    contact_name: str | None
    contact_avatar_url: str | None
    is_active: bool
    is_bot_active: bool
    is_unread: bool
    unread_count: int
    last_message_text: str | None
    last_message_at: datetime | None
    last_message_direction: str | None
    assigned_to_id: uuid.UUID | None
    tags: list[str]
    tenant_id: uuid.UUID
    lead_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ConversationWithMessages(ConversationResponse):
    """Conversa com mensagens incluídas."""
    messages: list[MessageResponse] = []


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    pages: int
    per_page: int


class ConversationUpdate(BaseModel):
    """Atualizar conversa."""
    is_bot_active: bool | None = None
    assigned_to_id: uuid.UUID | None = None
    tags: list[str] | None = None


class ConversationMarkRead(BaseModel):
    """Marcar como lida."""
    pass


class ConversationToggleBot(BaseModel):
    """Ativar/desativar bot."""
    is_active: bool
"""
Tipos de eventos WebSocket.

Define os eventos que podem ser enviados/recebidos via WebSocket.
"""
from enum import Enum


class WebSocketEventType(str, Enum):
    """Tipos de eventos WebSocket."""

    # ==================== CONEXÃO ====================
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_ERROR = "connection_error"

    # ==================== MENSAGENS ====================
    NEW_MESSAGE = "new_message"
    MESSAGE_STATUS_UPDATED = "message_status_updated"
    MESSAGES_READ = "messages_read"

    # ==================== CONVERSAS ====================
    CONVERSATION_UPDATED = "conversation_updated"
    CONVERSATION_ASSIGNED = "conversation_assigned"
    CONVERSATION_CLOSED = "conversation_closed"
    CONVERSATION_CREATED = "conversation_created"

    # ==================== AGENDAMENTOS ====================
    APPOINTMENT_CREATED = "appointment_created"
    APPOINTMENT_UPDATED = "appointment_updated"
    APPOINTMENT_CANCELLED = "appointment_cancelled"

    # ==================== LEADS ====================
    LEAD_CREATED = "lead_created"
    LEAD_UPDATED = "lead_updated"

    # ==================== AÇÕES DO CLIENTE ====================
    SUBSCRIBE_CONVERSATION = "subscribe_conversation"
    UNSUBSCRIBE_CONVERSATION = "unsubscribe_conversation"
    MARK_AS_READ = "mark_as_read"
    TYPING = "typing"
    USER_TYPING = "user_typing"

    # ==================== INSCRIÇÕES ====================
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"

    # ==================== SISTEMA ====================
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
"""
Exceções específicas do módulo Conversations.
"""
from app.core.exceptions import NotFoundException, BadRequestException


class ConversationNotFoundError(NotFoundException):
    def __init__(self, conversation_id: str | None = None):
        detail = "Conversa não encontrada"
        if conversation_id:
            detail = f"Conversa '{conversation_id}' não encontrada"
        super().__init__(detail=detail)


class MessageNotFoundError(NotFoundException):
    def __init__(self, message_id: str | None = None):
        detail = "Mensagem não encontrada"
        if message_id:
            detail = f"Mensagem '{message_id}' não encontrada"
        super().__init__(detail=detail)


class DuplicateMessageError(BadRequestException):
    def __init__(self, external_id: str):
        super().__init__(detail=f"Mensagem '{external_id}' já existe")
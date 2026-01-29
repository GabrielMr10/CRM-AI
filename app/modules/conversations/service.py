"""
Service - Lógica de negócio.
"""
import uuid
from math import ceil
from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.conversations.models import Conversation, Message, MessageDirection, MessageType
from app.modules.conversations.schemas import (
    ConversationResponse,
    ConversationListResponse,
    ConversationWithMessages,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    MessageFromWebhook,
)
from app.modules.conversations.repository import ConversationRepository, MessageRepository
from app.modules.conversations.exceptions import (
    ConversationNotFoundError,
    DuplicateMessageError,
)
from app.modules.users.models import User


class ConversationService:
    
    @staticmethod
    def get_or_404(
        db: Session,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Conversation:
        conversation = ConversationRepository.get_by_id_and_tenant(db, conversation_id, tenant_id)
        if not conversation:
            raise ConversationNotFoundError(str(conversation_id))
        return conversation
    
    @staticmethod
    def get_by_phone(
        db: Session,
        phone: str,
        tenant_id: uuid.UUID,
    ) -> Conversation | None:
        return ConversationRepository.get_by_phone(db, phone, tenant_id)
    
    @staticmethod
    def list_paginated(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
        is_unread: bool | None = None,
        assigned_to_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> ConversationListResponse:
        skip = (page - 1) * per_page
        
        conversations = ConversationRepository.get_all(
            db,
            tenant_id,
            skip=skip,
            limit=per_page,
            is_unread=is_unread,
            assigned_to_id=assigned_to_id,
            search=search,
        )
        
        total = ConversationRepository.count(db, tenant_id, is_unread=is_unread)
        pages = ceil(total / per_page) if total > 0 else 1
        
        return ConversationListResponse(
            items=[ConversationResponse.model_validate(c) for c in conversations],
            total=total,
            page=page,
            pages=pages,
            per_page=per_page,
        )
    
    @staticmethod
    def get_with_messages(
        db: Session,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        messages_limit: int = 50,
    ) -> ConversationWithMessages:
        conversation = ConversationService.get_or_404(db, conversation_id, tenant_id)
        messages = MessageRepository.get_by_conversation(
            db, conversation_id, limit=messages_limit
        )
        
        # Inverte para ordem cronológica
        messages_list = list(reversed(messages))
        
        return ConversationWithMessages(
            **ConversationResponse.model_validate(conversation).model_dump(),
            messages=[MessageResponse.model_validate(m) for m in messages_list],
        )
    
    @staticmethod
    def get_messages(
        db: Session,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        limit: int = 50,
        before: datetime | None = None,
    ) -> MessageListResponse:
        ConversationService.get_or_404(db, conversation_id, tenant_id)
        
        messages = MessageRepository.get_by_conversation(
            db, conversation_id, limit=limit + 1, before=before
        )
        
        has_more = len(messages) > limit
        messages_list = list(reversed(messages[:limit]))
        
        return MessageListResponse(
            items=[MessageResponse.model_validate(m) for m in messages_list],
            total=MessageRepository.count_by_conversation(db, conversation_id),
            has_more=has_more,
        )
    
    @staticmethod
    def receive_message(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        data: MessageFromWebhook,
    ) -> tuple[Conversation, Message]:
        """
        Processa mensagem recebida do webhook Z-API.
        Cria conversa se não existir.
        
        Retorna: (conversation, message)
        """
        # Verificar duplicata
        if data.external_id and MessageRepository.exists_external_id(db, data.external_id):
            raise DuplicateMessageError(data.external_id)
        
        # Obter ou criar conversa
        conversation, _ = ConversationRepository.get_or_create(
            db,
            phone=data.phone,
            tenant_id=tenant_id,
            contact_name=data.contact_name,
        )
        
        # Criar mensagem
        message = MessageRepository.create(
            db,
            conversation_id=conversation.id,
            tenant_id=tenant_id,
            content=data.content,
            message_type=data.message_type.value,
            direction=data.direction.value,
            external_id=data.external_id,
            media_url=data.media_url,
            media_mime_type=data.media_mime_type,
            media_filename=data.media_filename,
            raw_data=data.raw_data,
            whatsapp_timestamp=data.whatsapp_timestamp,
        )
        
        # Atualizar última mensagem
        ConversationRepository.update_last_message(db, conversation=conversation, message=message)
        
        return conversation, message
    
    @staticmethod
    def send_message(
        db: Session,
        *,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: MessageCreate,
        sent_by: User | None = None,
        sent_by_bot: bool = False,
        external_id: str | None = None,
        status: str | None = None,
    ) -> Message:
        """
        Registra mensagem enviada.
        A integração com Z-API é feita no módulo de integrations.
        """
        conversation = ConversationService.get_or_404(db, conversation_id, tenant_id)

        message = MessageRepository.create(
            db,
            conversation_id=conversation.id,
            tenant_id=tenant_id,
            content=data.content,
            message_type=data.message_type.value,
            direction=MessageDirection.OUTBOUND.value,
            external_id=external_id,
            sent_by_id=sent_by.id if sent_by else None,
            sent_by_bot=sent_by_bot,
            status=status,
        )
        
        # Atualizar última mensagem
        ConversationRepository.update_last_message(db, conversation=conversation, message=message)
        
        return message
    
    @staticmethod
    def mark_as_read(
        db: Session,
        *,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Conversation:
        conversation = ConversationService.get_or_404(db, conversation_id, tenant_id)
        return ConversationRepository.mark_as_read(db, conversation=conversation)
    
    @staticmethod
    def toggle_bot(
        db: Session,
        *,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        is_active: bool,
    ) -> Conversation:
        conversation = ConversationService.get_or_404(db, conversation_id, tenant_id)
        return ConversationRepository.update_bot_status(db, conversation=conversation, is_active=is_active)
    
    @staticmethod
    def assign(
        db: Session,
        *,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
    ) -> Conversation:
        conversation = ConversationService.get_or_404(db, conversation_id, tenant_id)
        return ConversationRepository.assign(db, conversation=conversation, user_id=user_id)
    
    @staticmethod
    def link_lead(
        db: Session,
        *,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> Conversation:
        conversation = ConversationService.get_or_404(db, conversation_id, tenant_id)
        return ConversationRepository.link_lead(db, conversation=conversation, lead_id=lead_id)
    
    @staticmethod
    def get_stats(db: Session, tenant_id: uuid.UUID) -> dict:
        """Estatísticas para dashboard."""
        total = ConversationRepository.count(db, tenant_id)
        unread = ConversationRepository.count(db, tenant_id, is_unread=True)
        
        return {
            "total_conversations": total,
            "unread_count": unread,
        }
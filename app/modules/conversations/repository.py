"""
Repository - Queries do banco de dados.
"""
import uuid
from typing import Sequence
from datetime import datetime, timezone

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.orm import Session, selectinload

from app.modules.conversations.models import Conversation, Message, MessageDirection
from app.modules.conversations.schemas import MessageFromWebhook


class ConversationRepository:
    
    @staticmethod
    def get_by_id(db: Session, conversation_id: uuid.UUID) -> Conversation | None:
        return db.get(Conversation, conversation_id)
    
    @staticmethod
    def get_by_id_and_tenant(
        db: Session,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            and_(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id)
        )
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_by_phone(
        db: Session,
        phone: str,
        tenant_id: uuid.UUID,
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            and_(Conversation.phone == phone, Conversation.tenant_id == tenant_id)
        )
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_all(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
        is_unread: bool | None = None,
        assigned_to_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> Sequence[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .order_by(Conversation.last_message_at.desc().nullslast())
        )
        
        if is_unread is not None:
            stmt = stmt.where(Conversation.is_unread == is_unread)
        
        if assigned_to_id:
            stmt = stmt.where(Conversation.assigned_to_id == assigned_to_id)
        
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Conversation.phone.ilike(search_term),
                    Conversation.contact_name.ilike(search_term),
                )
            )
        
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def count(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        is_unread: bool | None = None,
    ) -> int:
        stmt = select(func.count(Conversation.id)).where(Conversation.tenant_id == tenant_id)
        
        if is_unread is not None:
            stmt = stmt.where(Conversation.is_unread == is_unread)
        
        return db.execute(stmt).scalar_one()
    
    @staticmethod
    def create(
        db: Session,
        *,
        phone: str,
        tenant_id: uuid.UUID,
        contact_name: str | None = None,
        lead_id: uuid.UUID | None = None,
    ) -> Conversation:
        conversation = Conversation(
            phone=phone,
            tenant_id=tenant_id,
            contact_name=contact_name,
            lead_id=lead_id,
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    @staticmethod
    def get_or_create(
        db: Session,
        *,
        phone: str,
        tenant_id: uuid.UUID,
        contact_name: str | None = None,
    ) -> tuple[Conversation, bool]:
        """Retorna (conversation, criada: bool)."""
        existing = ConversationRepository.get_by_phone(db, phone, tenant_id)
        
        if existing:
            # Atualiza nome se veio novo
            if contact_name and not existing.contact_name:
                existing.contact_name = contact_name
                db.commit()
                db.refresh(existing)
            return existing, False
        
        conversation = ConversationRepository.create(
            db,
            phone=phone,
            tenant_id=tenant_id,
            contact_name=contact_name,
        )
        return conversation, True
    
    @staticmethod
    def update_last_message(
        db: Session,
        *,
        conversation: Conversation,
        message: Message,
    ) -> Conversation:
        """Atualiza dados da última mensagem."""
        conversation.last_message_text = (message.content or f"[{message.message_type}]")[:500]
        conversation.last_message_at = message.created_at
        conversation.last_message_direction = message.direction
        
        # Se recebida, marca como não lida
        if message.direction == MessageDirection.INBOUND.value:
            conversation.is_unread = True
            conversation.unread_count += 1
        
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    @staticmethod
    def mark_as_read(db: Session, *, conversation: Conversation) -> Conversation:
        conversation.is_unread = False
        conversation.unread_count = 0
        db.commit()
        db.refresh(conversation)
        return conversation
    
    @staticmethod
    def update_bot_status(
        db: Session,
        *,
        conversation: Conversation,
        is_active: bool,
    ) -> Conversation:
        conversation.is_bot_active = is_active
        db.commit()
        db.refresh(conversation)
        return conversation
    
    @staticmethod
    def assign(
        db: Session,
        *,
        conversation: Conversation,
        user_id: uuid.UUID | None,
    ) -> Conversation:
        conversation.assigned_to_id = user_id
        db.commit()
        db.refresh(conversation)
        return conversation
    
    @staticmethod
    def link_lead(
        db: Session,
        *,
        conversation: Conversation,
        lead_id: uuid.UUID,
    ) -> Conversation:
        conversation.lead_id = lead_id
        db.commit()
        db.refresh(conversation)
        return conversation


class MessageRepository:
    
    @staticmethod
    def get_by_id(db: Session, message_id: uuid.UUID) -> Message | None:
        return db.get(Message, message_id)
    
    @staticmethod
    def get_by_external_id(db: Session, external_id: str) -> Message | None:
        stmt = select(Message).where(Message.external_id == external_id)
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_by_conversation(
        db: Session,
        conversation_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
        before: datetime | None = None,
    ) -> Sequence[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        if before:
            stmt = stmt.where(Message.created_at < before)
        
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def count_by_conversation(db: Session, conversation_id: uuid.UUID) -> int:
        stmt = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        return db.execute(stmt).scalar_one()
    
    @staticmethod
    def exists_external_id(db: Session, external_id: str) -> bool:
        stmt = select(Message.id).where(Message.external_id == external_id)
        return db.execute(stmt).scalar_one_or_none() is not None
    
    @staticmethod
    def create(
        db: Session,
        *,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        content: str | None,
        message_type: str,
        direction: str,
        external_id: str | None = None,
        media_url: str | None = None,
        media_mime_type: str | None = None,
        media_filename: str | None = None,
        sent_by_id: uuid.UUID | None = None,
        sent_by_bot: bool = False,
        raw_data: dict | None = None,
        whatsapp_timestamp: datetime | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            content=content,
            message_type=message_type,
            direction=direction,
            external_id=external_id,
            media_url=media_url,
            media_mime_type=media_mime_type,
            media_filename=media_filename,
            sent_by_id=sent_by_id,
            sent_by_bot=sent_by_bot,
            raw_data=raw_data or {},
            whatsapp_timestamp=whatsapp_timestamp,
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        return message
    
    @staticmethod
    def update_status(
        db: Session,
        *,
        message: Message,
        status: str,
        delivered_at: datetime | None = None,
        read_at: datetime | None = None,
    ) -> Message:
        message.status = status
        if delivered_at:
            message.delivered_at = delivered_at
        if read_at:
            message.read_at = read_at
        db.commit()
        db.refresh(message)
        return message
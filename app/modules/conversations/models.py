"""
Models de Conversation e Message.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    from app.modules.tenants.models import Tenant
    from app.modules.leads.models import Lead
    from app.modules.users.models import User


class MessageDirection(str, Enum):
    """Direção da mensagem."""
    INBOUND = "inbound"    # Recebida do cliente
    OUTBOUND = "outbound"  # Enviada para o cliente


class MessageType(str, Enum):
    """Tipo de mensagem."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACT = "contact"
    BUTTON_REPLY = "button_reply"
    LIST_REPLY = "list_reply"
    TEMPLATE = "template"
    SYSTEM = "system"  # Mensagens do sistema (ex: "conversa iniciada")


class MessageStatus(str, Enum):
    """Status de envio da mensagem."""
    PENDING = "pending"      # Aguardando envio
    SENT = "sent"           # Enviada
    DELIVERED = "delivered"  # Entregue
    READ = "read"           # Lida
    FAILED = "failed"       # Falhou


class Conversation(Base):
    """
    Conversa com um contato.
    
    Uma conversation por telefone por tenant.
    """
    
    __tablename__ = "conversations"
    
    __table_args__ = (
        Index("ix_conversations_tenant_phone", "tenant_id", "phone", unique=True),
        Index("ix_conversations_tenant_last_message", "tenant_id", "last_message_at"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    # Identificação do contato
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Telefone do contato (WhatsApp)",
    )
    
    contact_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Nome do contato (do WhatsApp ou Lead)",
    )
    
    contact_avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL do avatar",
    )
    
    # Status da conversa
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Conversa ativa",
    )
    
    is_bot_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Bot (Laura) está ativo nesta conversa",
    )
    
    is_unread: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Tem mensagens não lidas",
    )
    
    unread_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Quantidade de mensagens não lidas",
    )
    
    # Última mensagem (para listagem)
    last_message_text: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Preview da última mensagem",
    )
    
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Data da última mensagem",
    )
    
    last_message_direction: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Direção da última mensagem",
    )
    
    # Atendimento
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Atendente responsável",
    )
    
    # Metadados
    metadata: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Dados extras da conversa",
    )
    
    tags: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Tags da conversa",
    )
    
    # Relacionamentos
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Lead vinculado",
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    lead: Mapped["Lead | None"] = relationship("Lead")
    assigned_to: Mapped["User | None"] = relationship("User")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    
    def __repr__(self) -> str:
        return f"<Conversation {self.phone}>"


class Message(Base):
    """
    Mensagem individual de uma conversa.
    """
    
    __tablename__ = "messages"
    
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_messages_external_id", "external_id"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    # ID externo (do Z-API)
    external_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment="ID da mensagem no Z-API/WhatsApp",
    )
    
    # Conteúdo
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Texto da mensagem",
    )
    
    message_type: Mapped[str] = mapped_column(
        String(50),
        default=MessageType.TEXT.value,
        nullable=False,
        comment="Tipo: text, image, audio, etc",
    )
    
    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="inbound ou outbound",
    )
    
    # Status (para outbound)
    status: Mapped[str] = mapped_column(
        String(20),
        default=MessageStatus.SENT.value,
        nullable=False,
        comment="Status de envio",
    )
    
    # Mídia (se aplicável)
    media_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="URL da mídia",
    )
    
    media_mime_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="MIME type da mídia",
    )
    
    media_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Nome do arquivo",
    )
    
    # Quem enviou (se outbound)
    sent_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Usuário que enviou (se manual)",
    )
    
    sent_by_bot: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Enviada pelo bot (Laura)",
    )
    
    # Metadados do Z-API
    raw_data: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Dados brutos do webhook",
    )
    
    # Relacionamentos
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Timestamps do WhatsApp
    whatsapp_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp original do WhatsApp",
    )
    
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    tenant: Mapped["Tenant"] = relationship("Tenant")
    sent_by: Mapped["User | None"] = relationship("User")
    
    def __repr__(self) -> str:
        return f"<Message {self.direction} {self.message_type}>"
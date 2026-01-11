"""
Schemas dos payloads de webhook.
"""
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


# ==================== Z-API SCHEMAS ====================

class ZAPIMessageReceived(BaseModel):
    """Mensagem recebida do Z-API."""
    
    # Identificação
    messageId: str = Field(..., description="ID da mensagem no WhatsApp")
    phone: str = Field(..., description="Telefone do remetente")
    fromMe: bool = Field(default=False, description="Se foi enviada por nós")
    
    # Conteúdo
    text: str | None = Field(None, description="Texto da mensagem")
    type: str = Field(default="text", description="Tipo: text, image, audio, etc")
    
    # Mídia (se aplicável)
    image: dict | None = None
    audio: dict | None = None
    video: dict | None = None
    document: dict | None = None
    sticker: dict | None = None
    
    # Contato
    senderName: str | None = Field(None, description="Nome do remetente")
    senderPhoto: str | None = Field(None, description="URL da foto")
    
    # Timestamp
    momment: int | None = Field(None, description="Timestamp Unix")
    
    # Extras
    instanceId: str | None = None
    
    class Config:
        extra = "allow"  # Aceita campos extras


class ZAPIMessageStatus(BaseModel):
    """Status de mensagem enviada."""
    
    messageId: str
    status: Literal["sent", "delivered", "read", "failed"]
    phone: str | None = None
    momment: int | None = None
    
    class Config:
        extra = "allow"


class ZAPIWebhookPayload(BaseModel):
    """Payload genérico do Z-API."""
    
    event: str = Field(..., description="Tipo do evento")
    instanceId: str | None = None
    data: dict = Field(default_factory=dict)
    
    class Config:
        extra = "allow"


# ==================== N8N SCHEMAS ====================

class N8NMessageSent(BaseModel):
    """Mensagem enviada pela Laura via n8n."""
    
    conversation_id: str | None = None
    phone: str
    content: str
    message_type: str = "text"
    external_id: str | None = None
    sent_by_bot: bool = True


class N8NLeadUpdate(BaseModel):
    """Atualização de lead via n8n."""
    
    phone: str
    lead_id: str | None = None
    
    # Campos para atualizar
    status: str | None = None
    score: int | None = None
    temperature: str | None = None
    interest: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None


class N8NCreateDeal(BaseModel):
    """Criar deal via n8n."""
    
    phone: str
    lead_id: str | None = None
    pipeline_id: str | None = None
    stage_id: str | None = None
    title: str
    value: float = 0


class N8NWebhookPayload(BaseModel):
    """Payload genérico do n8n."""
    
    action: str = Field(..., description="Ação: message_sent, lead_update, create_deal")
    tenant_id: str
    data: dict = Field(default_factory=dict)
    
    class Config:
        extra = "allow"


# ==================== RESPONSES ====================

class WebhookResponse(BaseModel):
    """Resposta padrão do webhook."""
    
    success: bool = True
    message: str = "OK"
    data: dict | None = None
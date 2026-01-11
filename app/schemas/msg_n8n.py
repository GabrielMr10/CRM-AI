"""
Schemas Pydantic para mensagens do n8n
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel


class N8NMessageSchema(BaseModel):
    """Schema para receber logs do n8n"""
    message: str
    lead_phone: Optional[str] = None
    lead_id: Optional[int] = None
    user_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class N8NWebhookRequest(BaseModel):
    """Schema para receber webhook do n8n"""
    message: str
    lead_id: Optional[int] = None
    user_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class N8NWebhookResponse(BaseModel):
    """Schema de resposta para webhook do n8n"""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


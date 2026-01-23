"""
Schemas Pydantic para o módulo de integrações.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum


class ConnectionState(str, Enum):
    """Estado da conexão WhatsApp."""
    OPEN = "open"
    CLOSE = "close"
    CONNECTING = "connecting"
    NOT_FOUND = "not_found"
    ERROR = "error"


class WhatsAppStatusResponse(BaseModel):
    """Resposta de status da conexão WhatsApp."""
    instance: str
    state: ConnectionState
    connected: bool
    phone_number: Optional[str] = None
    error: Optional[str] = None


class WhatsAppQRCodeResponse(BaseModel):
    """Resposta com QR Code para conexão."""
    instance: str
    base64: Optional[str] = None
    pairingCode: Optional[str] = None
    code: Optional[str] = None
    error: Optional[str] = None


class WhatsAppConnectResponse(BaseModel):
    """Resposta ao iniciar conexão WhatsApp."""
    instance: str
    status: str
    qrcode: Optional[WhatsAppQRCodeResponse] = None
    connection: Optional[WhatsAppStatusResponse] = None
    message: Optional[str] = None


class WhatsAppDisconnectResponse(BaseModel):
    """Resposta ao desconectar WhatsApp."""
    instance: str
    status: str
    message: Optional[str] = None


class EvolutionWebhookPayload(BaseModel):
    """Payload recebido do webhook da Evolution API."""
    event: str
    instance: str
    data: Dict[str, Any] = {}
    destination: Optional[str] = None
    date_time: Optional[str] = None
    sender: Optional[str] = None
    server_url: Optional[str] = None
    apikey: Optional[str] = None


class IntegrationStatusResponse(BaseModel):
    """Status geral de todas as integrações."""
    whatsapp: WhatsAppStatusResponse
    evolution_api: bool = True

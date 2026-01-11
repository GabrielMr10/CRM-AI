"""
Handler para webhooks do Z-API.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.modules.webhooks.schemas import ZAPIMessageReceived, ZAPIMessageStatus
from app.modules.conversations.models import MessageType, MessageDirection
from app.modules.conversations.schemas import MessageFromWebhook
from app.modules.conversations.service import ConversationService
from app.modules.conversations.exceptions import DuplicateMessageError
from app.modules.leads.schemas import LeadCreate
from app.modules.leads.service import LeadService


class ZAPIWebhookHandler:
    """Processa eventos do Z-API."""
    
    @staticmethod
    def handle_message_received(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        payload: ZAPIMessageReceived,
    ) -> dict:
        """
        Processa mensagem recebida.
        
        1. Cria/atualiza conversa
        2. Salva mensagem
        3. Cria lead se não existir
        4. Retorna dados para n8n processar
        """
        # Limpar telefone
        phone = ZAPIWebhookHandler._clean_phone(payload.phone)
        
        # Determinar tipo de mensagem
        message_type = ZAPIWebhookHandler._get_message_type(payload)
        
        # Extrair conteúdo e mídia
        content, media_url, media_mime, media_filename = ZAPIWebhookHandler._extract_content(payload)
        
        # Timestamp
        whatsapp_timestamp = None
        if payload.momment:
            whatsapp_timestamp = datetime.fromtimestamp(payload.momment, tz=timezone.utc)
        
        # Montar dados da mensagem
        message_data = MessageFromWebhook(
            external_id=payload.messageId,
            phone=phone,
            content=content,
            message_type=message_type,
            direction=MessageDirection.INBOUND,
            media_url=media_url,
            media_mime_type=media_mime,
            media_filename=media_filename,
            whatsapp_timestamp=whatsapp_timestamp,
            contact_name=payload.senderName,
            raw_data=payload.model_dump(),
        )
        
        # Salvar no banco
        try:
            conversation, message = ConversationService.receive_message(
                db,
                tenant_id=tenant_id,
                data=message_data,
            )
        except DuplicateMessageError:
            return {"success": True, "message": "Mensagem duplicada ignorada"}
        
        # Criar lead se não existir
        lead = None
        if not conversation.lead_id:
            lead_data = LeadCreate(
                name=payload.senderName or f"Lead {phone[-4:]}",
                phone=phone,
                source="whatsapp",
            )
            lead, created = LeadService.create_or_get(
                db,
                data=lead_data,
                tenant_id=tenant_id,
            )
            
            # Vincular lead à conversa
            if lead:
                ConversationService.link_lead(
                    db,
                    conversation_id=conversation.id,
                    tenant_id=tenant_id,
                    lead_id=lead.id,
                )
        
        return {
            "success": True,
            "conversation_id": str(conversation.id),
            "message_id": str(message.id),
            "lead_id": str(lead.id) if lead else str(conversation.lead_id) if conversation.lead_id else None,
            "is_bot_active": conversation.is_bot_active,
            "phone": phone,
            "content": content,
            "message_type": message_type.value if hasattr(message_type, 'value') else message_type,
        }
    
    @staticmethod
    def handle_message_status(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        payload: ZAPIMessageStatus,
    ) -> dict:
        """Atualiza status de mensagem enviada."""
        from app.modules.conversations.repository import MessageRepository
        
        message = MessageRepository.get_by_external_id(db, payload.messageId)
        
        if not message:
            return {"success": True, "message": "Mensagem não encontrada"}
        
        # Atualizar status
        delivered_at = None
        read_at = None
        
        if payload.status == "delivered" and payload.momment:
            delivered_at = datetime.fromtimestamp(payload.momment, tz=timezone.utc)
        elif payload.status == "read" and payload.momment:
            read_at = datetime.fromtimestamp(payload.momment, tz=timezone.utc)
        
        MessageRepository.update_status(
            db,
            message=message,
            status=payload.status,
            delivered_at=delivered_at,
            read_at=read_at,
        )
        
        return {"success": True, "status": payload.status}
    
    @staticmethod
    def _clean_phone(phone: str) -> str:
        """Remove caracteres não numéricos."""
        import re
        cleaned = re.sub(r"\D", "", phone)
        # Remover @c.us se presente
        cleaned = cleaned.replace("c.us", "").replace("@", "")
        return cleaned
    
    @staticmethod
    def _get_message_type(payload: ZAPIMessageReceived) -> MessageType:
        """Determina tipo da mensagem."""
        type_map = {
            "text": MessageType.TEXT,
            "image": MessageType.IMAGE,
            "audio": MessageType.AUDIO,
            "ptt": MessageType.AUDIO,  # Push-to-talk
            "video": MessageType.VIDEO,
            "document": MessageType.DOCUMENT,
            "sticker": MessageType.STICKER,
            "location": MessageType.LOCATION,
            "contact": MessageType.CONTACT,
            "button_reply": MessageType.BUTTON_REPLY,
            "list_reply": MessageType.LIST_REPLY,
        }
        return type_map.get(payload.type, MessageType.TEXT)
    
    @staticmethod
    def _extract_content(payload: ZAPIMessageReceived) -> tuple:
        """Extrai conteúdo e dados de mídia."""
        content = payload.text
        media_url = None
        media_mime = None
        media_filename = None
        
        if payload.image:
            media_url = payload.image.get("imageUrl") or payload.image.get("url")
            media_mime = payload.image.get("mimetype", "image/jpeg")
            content = payload.image.get("caption", content)
        
        elif payload.audio:
            media_url = payload.audio.get("audioUrl") or payload.audio.get("url")
            media_mime = payload.audio.get("mimetype", "audio/ogg")
        
        elif payload.video:
            media_url = payload.video.get("videoUrl") or payload.video.get("url")
            media_mime = payload.video.get("mimetype", "video/mp4")
            content = payload.video.get("caption", content)
        
        elif payload.document:
            media_url = payload.document.get("documentUrl") or payload.document.get("url")
            media_mime = payload.document.get("mimetype")
            media_filename = payload.document.get("fileName")
        
        elif payload.sticker:
            media_url = payload.sticker.get("stickerUrl") or payload.sticker.get("url")
            media_mime = "image/webp"
        
        return content, media_url, media_mime, media_filename
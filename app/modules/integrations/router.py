"""
Router - Endpoints da API de Integrações.

Prefixo: /api/v1/integrations
Tags: ["Integrations"]

USO:
    from app.modules.integrations.router import router as integrations_router
    app.include_router(integrations_router, prefix="/api/v1/integrations", tags=["Integrations"])
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from typing import Dict, Any
import logging

from app.core.dependencies import get_current_user, get_current_tenant

from .service import integration_service
from .schemas import (
    WhatsAppStatusResponse,
    WhatsAppConnectResponse,
    WhatsAppQRCodeResponse,
    WhatsAppDisconnectResponse,
    EvolutionWebhookPayload,
    IntegrationStatusResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== WHATSAPP ====================

@router.get(
    "/whatsapp/status",
    response_model=WhatsAppStatusResponse,
    summary="Status da conexão WhatsApp"
)
async def get_whatsapp_status(
    tenant=Depends(get_current_tenant)
):
    """
    Verifica o status atual da conexão WhatsApp do tenant.

    Retorna:
    - **connected**: true se WhatsApp está conectado
    - **state**: open, close, connecting, not_found, error
    """
    return await integration_service.get_whatsapp_status(tenant.id)


@router.post(
    "/whatsapp/connect",
    response_model=WhatsAppConnectResponse,
    summary="Conectar WhatsApp"
)
async def connect_whatsapp(
    tenant=Depends(get_current_tenant)
):
    """
    Inicia o processo de conexão do WhatsApp.

    - Se já conectado, retorna status "already_connected"
    - Se desconectado, cria instância e retorna QR Code

    O QR Code retornado em `base64` pode ser exibido diretamente:
    ```html
    <img src="data:image/png;base64,{qrcode.base64}" />
    ```
    """
    return await integration_service.connect_whatsapp(tenant.id)


@router.post(
    "/whatsapp/qrcode/refresh",
    response_model=WhatsAppQRCodeResponse,
    summary="Atualizar QR Code"
)
async def refresh_qrcode(
    tenant=Depends(get_current_tenant)
):
    """
    Gera um novo QR Code caso o anterior tenha expirado.
    O QR Code do WhatsApp expira após alguns segundos.
    """
    return await integration_service.refresh_qrcode(tenant.id)


@router.post(
    "/whatsapp/disconnect",
    response_model=WhatsAppDisconnectResponse,
    summary="Desconectar WhatsApp"
)
async def disconnect_whatsapp(
    tenant=Depends(get_current_tenant)
):
    """
    Desconecta o WhatsApp (logout).
    A instância continua existindo e pode ser reconectada.
    """
    return await integration_service.disconnect_whatsapp(tenant.id)


@router.delete(
    "/whatsapp/instance",
    response_model=WhatsAppDisconnectResponse,
    summary="Remover instância WhatsApp"
)
async def delete_whatsapp_instance(
    tenant=Depends(get_current_tenant)
):
    """
    Remove completamente a instância WhatsApp.
    Use apenas para reset total da integração.
    Após remover, será necessário gerar novo QR Code.
    """
    return await integration_service.delete_whatsapp_instance(tenant.id)


# ==================== WEBHOOK EVOLUTION ====================

@router.post(
    "/webhook/evolution",
    summary="Webhook Evolution API",
    include_in_schema=False  # Oculta da documentação pública
)
async def evolution_webhook(
    payload: EvolutionWebhookPayload,
    background_tasks: BackgroundTasks
):
    """
    Recebe eventos da Evolution API.

    Eventos tratados:
    - CONNECTION_UPDATE: Notifica frontend sobre mudança de conexão
    - QRCODE_UPDATED: Notifica frontend com novo QR Code
    - MESSAGES_UPSERT: Nova mensagem recebida
    - MESSAGES_UPDATE: Status de mensagem atualizado
    """
    logger.info(f"[Evolution Webhook] Evento: {payload.event}, Instância: {payload.instance}")

    # Extrai tenant_id do nome da instância (tenant_UUID)
    instance_name = payload.instance
    if instance_name.startswith("tenant_"):
        tenant_id = instance_name.replace("tenant_", "")
    else:
        logger.warning(f"Instância não segue padrão tenant_: {instance_name}")
        return {"status": "ignored"}

    # Processa eventos em background
    background_tasks.add_task(
        process_evolution_event,
        tenant_id=tenant_id,
        event=payload.event,
        data=payload.data
    )

    return {"status": "received"}


async def process_evolution_event(tenant_id: str, event: str, data: Dict[str, Any]):
    """Processa eventos da Evolution API e notifica via WebSocket."""
    from app.core.websocket_manager import ws_manager

    try:
        if event == "CONNECTION_UPDATE":
            # Notifica frontend sobre mudança de conexão
            state = data.get("state", "unknown")
            await ws_manager.send_to_tenant(tenant_id, {
                "type": "whatsapp_connection_update",
                "state": state,
                "connected": state == "open"
            })
            logger.info(f"[Tenant {tenant_id}] Conexão WhatsApp: {state}")

        elif event == "QRCODE_UPDATED":
            # Notifica frontend com novo QR Code
            qrcode_data = data.get("qrcode", {})
            await ws_manager.send_to_tenant(tenant_id, {
                "type": "whatsapp_qrcode_updated",
                "base64": qrcode_data.get("base64"),
                "pairingCode": qrcode_data.get("pairingCode")
            })
            logger.info(f"[Tenant {tenant_id}] QR Code atualizado")

        elif event == "MESSAGES_UPSERT":
            # Nova mensagem recebida - processa e salva no banco
            await _process_messages_upsert(tenant_id, data)

        elif event == "MESSAGES_UPDATE":
            # Atualização de status de mensagem (delivered, read)
            # TODO: Atualizar status no banco e notificar
            logger.info(f"[Tenant {tenant_id}] Status de mensagem atualizado")
            await ws_manager.send_to_tenant(tenant_id, {
                "type": "whatsapp_message_status",
                "data": data
            })

        elif event == "SEND_MESSAGE":
            # Confirmação de mensagem enviada
            logger.debug(f"[Tenant {tenant_id}] Mensagem enviada confirmada")

        else:
            logger.debug(f"[Tenant {tenant_id}] Evento não tratado: {event}")

    except Exception as e:
        logger.error(f"Erro ao processar evento {event}: {e}")


async def _process_messages_upsert(tenant_id: str, data: Dict[str, Any]):
    """
    Processa evento MESSAGES_UPSERT da Evolution API.
    Salva mensagem no banco e notifica via WebSocket.
    """
    from uuid import UUID
    from datetime import datetime, timezone
    from app.core.database import SessionLocal
    from app.core.websocket_manager import ws_manager
    from app.modules.conversations.service import ConversationService
    from app.modules.conversations.schemas import MessageFromWebhook
    from app.modules.conversations.models import MessageType, MessageDirection
    from app.modules.conversations.exceptions import DuplicateMessageError

    print(f"📩 [Evolution MESSAGES_UPSERT] Processando: {data}")

    try:
        # Evolution API envia mensagens em diferentes formatos
        # Pode ser uma lista ou objeto único
        messages = data.get("messages", [data]) if "messages" not in data else data.get("messages", [])
        if not isinstance(messages, list):
            messages = [messages]

        for msg in messages:
            # Extrai dados da mensagem
            key = msg.get("key", {})
            message_content = msg.get("message", {})

            # Ignora mensagens enviadas por nós (fromMe = true)
            if key.get("fromMe", False):
                logger.debug(f"[Tenant {tenant_id}] Mensagem própria ignorada")
                continue

            # Extrai telefone (remove @s.whatsapp.net)
            remote_jid = key.get("remoteJid", "")
            phone = remote_jid.replace("@s.whatsapp.net", "").replace("@g.us", "")

            if not phone:
                logger.warning(f"[Tenant {tenant_id}] Telefone não encontrado na mensagem")
                continue

            # Extrai ID externo
            external_id = key.get("id", "")

            # Extrai conteúdo da mensagem (diferentes formatos)
            content = (
                message_content.get("conversation") or
                message_content.get("extendedTextMessage", {}).get("text") or
                message_content.get("imageMessage", {}).get("caption") or
                message_content.get("videoMessage", {}).get("caption") or
                message_content.get("documentMessage", {}).get("caption") or
                ""
            )

            # Determina tipo de mensagem
            msg_type = MessageType.TEXT
            media_url = None
            media_mime_type = None

            if "imageMessage" in message_content:
                msg_type = MessageType.IMAGE
                media_mime_type = message_content.get("imageMessage", {}).get("mimetype")
            elif "audioMessage" in message_content:
                msg_type = MessageType.AUDIO
                media_mime_type = message_content.get("audioMessage", {}).get("mimetype")
            elif "videoMessage" in message_content:
                msg_type = MessageType.VIDEO
                media_mime_type = message_content.get("videoMessage", {}).get("mimetype")
            elif "documentMessage" in message_content:
                msg_type = MessageType.DOCUMENT
                media_mime_type = message_content.get("documentMessage", {}).get("mimetype")
            elif "stickerMessage" in message_content:
                msg_type = MessageType.STICKER
            elif "locationMessage" in message_content:
                msg_type = MessageType.LOCATION
                loc = message_content.get("locationMessage", {})
                content = f"Localização: {loc.get('degreesLatitude')}, {loc.get('degreesLongitude')}"
            elif "contactMessage" in message_content:
                msg_type = MessageType.CONTACT
                contact = message_content.get("contactMessage", {})
                content = f"Contato: {contact.get('displayName', 'Desconhecido')}"

            # Extrai nome do contato
            contact_name = msg.get("pushName", "")

            # Timestamp
            timestamp = msg.get("messageTimestamp")
            whatsapp_timestamp = None
            if timestamp:
                try:
                    whatsapp_timestamp = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
                except Exception:
                    whatsapp_timestamp = datetime.now(timezone.utc)
            else:
                whatsapp_timestamp = datetime.now(timezone.utc)

            print(f"📩 [Evolution] Telefone: {phone}, Conteúdo: {content[:50]}..., Tipo: {msg_type}")

            # Salva no banco de dados
            db = SessionLocal()
            try:
                tenant_uuid = UUID(tenant_id)

                message_data = MessageFromWebhook(
                    external_id=external_id,
                    phone=phone,
                    content=content or f"[{msg_type.value}]",
                    message_type=msg_type,
                    direction=MessageDirection.INBOUND,
                    contact_name=contact_name,
                    media_url=media_url,
                    media_mime_type=media_mime_type,
                    whatsapp_timestamp=whatsapp_timestamp,
                    raw_data=msg,
                )

                conversation, message = ConversationService.receive_message(
                    db,
                    tenant_id=tenant_uuid,
                    data=message_data,
                )

                logger.info(f"[Tenant {tenant_id}] Mensagem salva: {message.id}")

                # Notifica via WebSocket
                await ws_manager.broadcast_new_message(
                    tenant_id=tenant_id,
                    conversation_id=str(conversation.id),
                    message={
                        "id": str(message.id),
                        "content": message.content,
                        "direction": "inbound",
                        "message_type": msg_type.value,
                        "created_at": message.created_at.isoformat(),
                        "sender_name": contact_name or phone,
                        "sender_phone": phone,
                        "external_id": external_id,
                    }
                )

            except DuplicateMessageError:
                logger.debug(f"[Tenant {tenant_id}] Mensagem duplicada ignorada: {external_id}")
            except Exception as e:
                logger.error(f"[Tenant {tenant_id}] Erro ao salvar mensagem: {e}")
                import traceback
                traceback.print_exc()
            finally:
                db.close()

    except Exception as e:
        logger.error(f"[Tenant {tenant_id}] Erro ao processar MESSAGES_UPSERT: {e}")
        import traceback
        traceback.print_exc()


# ==================== HEALTH CHECK ====================

@router.get(
    "/health",
    summary="Verificar conexão com Evolution API"
)
async def check_evolution_health():
    """
    Verifica se a Evolution API está acessível.
    Não requer autenticação - útil para debug.
    """
    from .evolution_client import evolution_client
    from app.core.config import settings

    is_connected = await evolution_client.check_connection()

    return {
        "evolution_api": {
            "url": settings.EVOLUTION_API_URL,
            "connected": is_connected,
            "status": "ok" if is_connected else "unreachable"
        }
    }


# ==================== STATUS GERAL ====================

@router.get(
    "/status",
    response_model=IntegrationStatusResponse,
    summary="Status de todas integrações"
)
async def get_all_integrations_status(
    tenant=Depends(get_current_tenant)
):
    """
    Retorna o status de todas as integrações do tenant.
    Útil para exibir um dashboard de integrações.
    """
    whatsapp_status = await integration_service.get_whatsapp_status(tenant.id)

    return IntegrationStatusResponse(
        whatsapp=whatsapp_status,
        evolution_api=True  # Se chegou aqui, a API está funcionando
    )

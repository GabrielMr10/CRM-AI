"""
Router - Endpoints de webhooks.
"""
import logging
from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.websocket_manager import ws_manager
from app.modules.webhooks.schemas import (
    ZAPIMessageReceived,
    ZAPIMessageStatus,
    ZAPIWebhookPayload,
    N8NWebhookPayload,
    WebhookResponse,
)
from app.modules.webhooks.handlers.zapi import ZAPIWebhookHandler
from app.modules.webhooks.handlers.n8n import N8NWebhookHandler
from app.modules.webhooks.security import verify_zapi_webhook, verify_n8n_webhook
from app.modules.tenants.repository import TenantRepository

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Z-API WEBHOOKS ====================

@router.post(
    "/zapi/{tenant_id}",
    response_model=WebhookResponse,
    summary="Webhook Z-API",
    description="Recebe eventos do Z-API (mensagens, status, etc)",
)
async def zapi_webhook(
    tenant_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth: dict = Depends(verify_zapi_webhook),
):
    """
    Endpoint para receber webhooks do Z-API.

    URL para configurar no Z-API:
    https://seu-crm.com/api/v1/webhooks/zapi/{tenant_id}
    """
    from uuid import UUID

    # Validar tenant
    try:
        tenant_uuid = UUID(tenant_id)
        tenant = TenantRepository.get_by_id(db, tenant_uuid)
    except ValueError:
        return WebhookResponse(success=False, message="Tenant inválido")

    if not tenant:
        return WebhookResponse(success=False, message="Tenant não encontrado")

    # Parsear body
    body = await request.json()

    # Identificar tipo de evento
    # Z-API pode enviar diferentes formatos

    # Mensagem recebida
    if "messageId" in body and "phone" in body:
        # Ignorar mensagens enviadas por nós
        if body.get("fromMe", False):
            return WebhookResponse(success=True, message="Mensagem própria ignorada")

        try:
            payload = ZAPIMessageReceived(**body)
            result = ZAPIWebhookHandler.handle_message_received(
                db,
                tenant_id=tenant_uuid,
                payload=payload,
            )

            # Notifica via WebSocket em background
            if result.get("conversation_id") and result.get("message_id"):
                background_tasks.add_task(
                    _notify_websocket_zapi_message,
                    tenant_id=tenant_id,
                    result=result,
                    payload=payload,
                )

            return WebhookResponse(success=True, data=result)
        except Exception as e:
            return WebhookResponse(success=False, message=str(e))

    # Status de mensagem
    if "status" in body and "messageId" in body:
        try:
            payload = ZAPIMessageStatus(**body)
            result = ZAPIWebhookHandler.handle_message_status(
                db,
                tenant_id=tenant_uuid,
                payload=payload,
            )

            # Notifica status via WebSocket
            if result.get("conversation_id") and result.get("message_id"):
                background_tasks.add_task(
                    _notify_websocket_zapi_status,
                    tenant_id=tenant_id,
                    result=result,
                    status=payload.status,
                )

            return WebhookResponse(success=True, data=result)
        except Exception as e:
            return WebhookResponse(success=False, message=str(e))

    # Evento não tratado
    return WebhookResponse(
        success=True,
        message="Evento recebido mas não processado",
        data={"raw": body},
    )


async def _notify_websocket_zapi_message(
    tenant_id: str,
    result: dict,
    payload: ZAPIMessageReceived,
):
    """Notifica nova mensagem recebida via Z-API."""
    try:
        conversation_id = result.get("conversation_id")
        message_id = result.get("message_id")

        await ws_manager.broadcast_new_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            message_data={
                "id": message_id,
                "content": result.get("content", payload.text or ""),
                "sent_by_bot": False,
                "message_type": result.get("message_type", payload.type or "text"),
                "phone": payload.phone,
                "external_id": payload.messageId,
            }
        )
        logger.info(f"[WS] Nova mensagem Z-API notificada - tenant: {tenant_id}")

    except Exception as e:
        logger.error(f"Erro ao notificar WebSocket (Z-API message): {e}")


async def _notify_websocket_zapi_status(
    tenant_id: str,
    result: dict,
    status: str,
):
    """Notifica atualização de status de mensagem via Z-API."""
    try:
        conversation_id = result.get("conversation_id")
        message_id = result.get("message_id")

        await ws_manager.broadcast_message_status(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            message_id=message_id,
            status=status,
        )
        logger.info(f"[WS] Status Z-API notificado: {status} - tenant: {tenant_id}")

    except Exception as e:
        logger.error(f"Erro ao notificar WebSocket (Z-API status): {e}")


# ==================== N8N WEBHOOKS ====================

@router.post(
    "/n8n",
    response_model=WebhookResponse,
    summary="Webhook n8n",
    description="Recebe callbacks do n8n (mensagens enviadas, updates de lead, etc)",
)
async def n8n_webhook(
    payload: N8NWebhookPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth: dict = Depends(verify_n8n_webhook),
):
    """
    Endpoint para n8n enviar callbacks.

    Headers necessários:
    - X-Tenant-Id: UUID do tenant
    - X-Webhook-Token: Token configurado no tenant (opcional)

    Actions suportadas:
    - message_sent: Registra mensagem enviada pela Laura
    - lead_update: Atualiza dados do lead
    - create_deal: Cria deal no pipeline
    """
    tenant_id = auth["tenant_id"]

    result = N8NWebhookHandler.dispatch(
        db,
        tenant_id=tenant_id,
        action=payload.action,
        data=payload.data,
    )

    # Notifica via WebSocket em background se a ação foi bem-sucedida
    if result.get("success"):
        background_tasks.add_task(
            _notify_websocket_n8n,
            tenant_id=str(tenant_id),
            action=payload.action,
            result=result,
            original_data=payload.data,
        )

    return WebhookResponse(
        success=result.get("success", False),
        message=result.get("error", "OK"),
        data=result,
    )


async def _notify_websocket_n8n(
    tenant_id: str,
    action: str,
    result: dict,
    original_data: dict,
):
    """Envia notificação via WebSocket baseado na ação do n8n."""
    try:
        if action == "message_sent":
            # Notifica nova mensagem enviada pelo bot
            conversation_id = result.get("conversation_id")
            message_id = result.get("message_id")

            if conversation_id and message_id:
                await ws_manager.broadcast_new_message(
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    message_data={
                        "id": message_id,
                        "content": original_data.get("content", ""),
                        "sent_by_bot": True,
                        "message_type": original_data.get("message_type", "text"),
                    }
                )
                logger.info(f"[WS] Notificação message_sent enviada - tenant: {tenant_id}")

        elif action == "lead_update":
            # Notifica atualização de lead
            lead_id = result.get("lead_id")
            if lead_id:
                await ws_manager.send_to_tenant(tenant_id, {
                    "type": "lead_updated",
                    "lead_id": lead_id,
                    "updated_fields": result.get("updated_fields", []),
                })
                logger.info(f"[WS] Notificação lead_update enviada - tenant: {tenant_id}")

        elif action == "create_deal":
            # Notifica criação de deal
            deal_id = result.get("deal_id")
            if deal_id:
                await ws_manager.send_to_tenant(tenant_id, {
                    "type": "deal_created",
                    "deal_id": deal_id,
                    "pipeline_id": result.get("pipeline_id"),
                    "stage_id": result.get("stage_id"),
                })
                logger.info(f"[WS] Notificação deal_created enviada - tenant: {tenant_id}")

    except Exception as e:
        logger.error(f"Erro ao notificar WebSocket (n8n): {e}")


# ==================== HEALTH CHECK ====================

@router.get(
    "/health",
    summary="Health check webhooks",
)
async def webhook_health():
    """Verifica se o endpoint de webhooks está funcionando."""
    return {"status": "ok", "message": "Webhooks endpoint is healthy"}
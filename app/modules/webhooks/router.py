"""
Router - Endpoints de webhooks.
"""
from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
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
            return WebhookResponse(success=True, data=result)
        except Exception as e:
            return WebhookResponse(success=False, message=str(e))
    
    # Evento não tratado
    return WebhookResponse(
        success=True,
        message="Evento recebido mas não processado",
        data={"raw": body},
    )


# ==================== N8N WEBHOOKS ====================

@router.post(
    "/n8n",
    response_model=WebhookResponse,
    summary="Webhook n8n",
    description="Recebe callbacks do n8n (mensagens enviadas, updates de lead, etc)",
)
async def n8n_webhook(
    payload: N8NWebhookPayload,
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
    result = N8NWebhookHandler.dispatch(
        db,
        tenant_id=auth["tenant_id"],
        action=payload.action,
        data=payload.data,
    )
    
    return WebhookResponse(
        success=result.get("success", False),
        message=result.get("error", "OK"),
        data=result,
    )


# ==================== HEALTH CHECK ====================

@router.get(
    "/health",
    summary="Health check webhooks",
)
async def webhook_health():
    """Verifica se o endpoint de webhooks está funcionando."""
    return {"status": "ok", "message": "Webhooks endpoint is healthy"}
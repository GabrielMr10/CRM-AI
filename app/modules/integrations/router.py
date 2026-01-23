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
            # Nova mensagem recebida
            # TODO: Integrar com módulo de conversas para salvar e notificar
            logger.info(f"[Tenant {tenant_id}] Nova mensagem recebida")
            await ws_manager.send_to_tenant(tenant_id, {
                "type": "whatsapp_new_message",
                "data": data
            })

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

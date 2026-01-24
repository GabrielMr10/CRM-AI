"""
Service - Lógica de negócio para integrações.

USO:
    from app.modules.integrations.service import integration_service

    status = await integration_service.get_whatsapp_status(tenant_id)
"""
from uuid import UUID
import logging

from .evolution_client import evolution_client
from .schemas import (
    WhatsAppStatusResponse,
    WhatsAppQRCodeResponse,
    WhatsAppConnectResponse,
    WhatsAppDisconnectResponse,
    ConnectionState
)
from .exceptions import (
    EvolutionAPIException,
    QRCodeGenerationException
)

logger = logging.getLogger(__name__)


class IntegrationService:
    """Serviço para gerenciar integrações do tenant."""

    async def get_whatsapp_status(self, tenant_id: UUID) -> WhatsAppStatusResponse:
        """Verifica o status da conexão WhatsApp do tenant."""
        try:
            result = await evolution_client.get_connection_state(str(tenant_id))

            # Mapeia o estado para o enum
            state_map = {
                "open": ConnectionState.OPEN,
                "close": ConnectionState.CLOSE,
                "connecting": ConnectionState.CONNECTING,
                "not_found": ConnectionState.NOT_FOUND,
                "error": ConnectionState.ERROR,
            }

            state = state_map.get(result.get("state", "error"), ConnectionState.ERROR)

            return WhatsAppStatusResponse(
                instance=result["instance"],
                state=state,
                connected=result.get("connected", False),
                error=result.get("error")
            )
        except Exception as e:
            logger.error(f"Erro ao verificar status WhatsApp: {e}")
            return WhatsAppStatusResponse(
                instance=f"tenant_{tenant_id}",
                state=ConnectionState.ERROR,
                connected=False,
                error=str(e)
            )

    async def connect_whatsapp(self, tenant_id: UUID) -> WhatsAppConnectResponse:
        """
        Inicia o processo de conexão do WhatsApp.
        - Se já conectado, retorna status
        - Se instância existe mas desconectada, gera QR Code
        - Se instância não existe, cria e gera QR Code
        """
        tenant_str = str(tenant_id)

        try:
            # 1. Verifica se já está conectado
            status = await evolution_client.get_connection_state(tenant_str)

            if status.get("connected"):
                return WhatsAppConnectResponse(
                    instance=status["instance"],
                    status="already_connected",
                    connection=WhatsAppStatusResponse(
                        instance=status["instance"],
                        state=ConnectionState.OPEN,
                        connected=True
                    ),
                    message="WhatsApp já está conectado"
                )

            # 2. Tenta criar instância (ignora se já existe)
            try:
                await evolution_client.create_instance(tenant_str)
            except Exception as e:
                # Ignora erro de "já existe"
                error_str = str(e).lower()
                if "already in use" not in error_str and "403" not in error_str and "409" not in error_str:
                    raise
                logger.info(f"Instância já existe, continuando para QR Code...")

            # 3. Gera QR Code
            qr_result = await evolution_client.get_qrcode(tenant_str)

            if not qr_result.get("base64"):
                # Talvez já esteja conectado após criar
                status = await evolution_client.get_connection_state(tenant_str)
                if status.get("connected"):
                    return WhatsAppConnectResponse(
                        instance=status["instance"],
                        status="already_connected",
                        connection=WhatsAppStatusResponse(
                            instance=status["instance"],
                            state=ConnectionState.OPEN,
                            connected=True
                        ),
                        message="WhatsApp já está conectado"
                    )
                raise QRCodeGenerationException()

            return WhatsAppConnectResponse(
                instance=qr_result["instance"],
                status="qrcode_ready",
                qrcode=WhatsAppQRCodeResponse(
                    instance=qr_result["instance"],
                    base64=qr_result.get("base64"),
                    pairingCode=qr_result.get("pairingCode"),
                    code=qr_result.get("code")
                ),
                message="Escaneie o QR Code com seu WhatsApp"
            )

        except QRCodeGenerationException:
            raise
        except Exception as e:
            logger.error(f"Erro ao conectar WhatsApp: {e}")
            raise EvolutionAPIException(f"Erro ao conectar: {str(e)}")

    async def refresh_qrcode(self, tenant_id: UUID) -> WhatsAppQRCodeResponse:
        """Gera um novo QR Code."""
        tenant_str = str(tenant_id)

        try:
            # Reinicia para gerar novo QR
            await evolution_client.restart_instance(tenant_str)

            # Obtém novo QR Code
            qr_result = await evolution_client.get_qrcode(tenant_str)

            if not qr_result.get("base64"):
                raise QRCodeGenerationException()

            return WhatsAppQRCodeResponse(
                instance=qr_result["instance"],
                base64=qr_result.get("base64"),
                pairingCode=qr_result.get("pairingCode"),
                code=qr_result.get("code")
            )

        except Exception as e:
            logger.error(f"Erro ao atualizar QR Code: {e}")
            raise QRCodeGenerationException()

    async def disconnect_whatsapp(self, tenant_id: UUID) -> WhatsAppDisconnectResponse:
        """Desconecta o WhatsApp (logout)."""
        tenant_str = str(tenant_id)

        try:
            result = await evolution_client.logout(tenant_str)

            return WhatsAppDisconnectResponse(
                instance=result["instance"],
                status=result["status"],
                message="WhatsApp desconectado com sucesso"
            )

        except Exception as e:
            logger.error(f"Erro ao desconectar WhatsApp: {e}")
            raise EvolutionAPIException(f"Erro ao desconectar: {str(e)}")

    async def delete_whatsapp_instance(self, tenant_id: UUID) -> WhatsAppDisconnectResponse:
        """Remove completamente a instância (para reset total)."""
        tenant_str = str(tenant_id)

        try:
            # Primeiro faz logout
            try:
                await evolution_client.logout(tenant_str)
            except Exception:
                pass  # Ignora erro de logout se não estava conectado

            # Depois deleta
            result = await evolution_client.delete_instance(tenant_str)

            return WhatsAppDisconnectResponse(
                instance=result["instance"],
                status=result["status"],
                message="Instância removida completamente"
            )

        except Exception as e:
            logger.error(f"Erro ao deletar instância: {e}")
            raise EvolutionAPIException(f"Erro ao deletar: {str(e)}")


# Instância singleton
integration_service = IntegrationService()

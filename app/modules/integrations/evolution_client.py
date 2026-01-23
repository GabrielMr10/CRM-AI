"""
Cliente HTTP para comunicação com a Evolution API.

Documentação: https://doc.evolution-api.com/

USO:
    from app.modules.integrations.evolution_client import evolution_client

    result = await evolution_client.get_connection_state("tenant-uuid")
"""
import httpx
from typing import Dict, Any
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EvolutionAPIClient:
    """
    Cliente HTTP para comunicação com a Evolution API.
    Cada tenant tem sua própria instância identificada por tenant_UUID.
    """

    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL.rstrip('/')
        self.api_key = settings.EVOLUTION_API_KEY
        self.webhook_url = settings.EVOLUTION_WEBHOOK_URL
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    def _get_instance_name(self, tenant_id: str) -> str:
        """Gera nome único da instância baseado no tenant_id."""
        return f"tenant_{tenant_id}"

    async def create_instance(self, tenant_id: str) -> Dict[str, Any]:
        """
        Cria uma nova instância na Evolution API para o tenant.
        Se já existir, retorna a existente.
        """
        instance_name = self._get_instance_name(tenant_id)

        payload = {
            "instanceName": instance_name,
            "token": tenant_id,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
            "webhook": {
                "url": self.webhook_url,
                "byEvents": True,
                "base64": False,
                "events": [
                    "CONNECTION_UPDATE",
                    "MESSAGES_UPSERT",
                    "MESSAGES_UPDATE",
                    "MESSAGES_DELETE",
                    "SEND_MESSAGE",
                    "QRCODE_UPDATED"
                ]
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/instance/create",
                    json=payload,
                    headers=self.headers
                )

                # Se já existe (409), não é erro
                if response.status_code in [200, 201]:
                    logger.info(f"Instância criada: {instance_name}")
                    return response.json()
                elif response.status_code == 409:
                    logger.info(f"Instância já existe: {instance_name}")
                    return {"instance": instance_name, "status": "exists"}

                logger.error(f"Erro ao criar instância: {response.status_code} - {response.text}")
                response.raise_for_status()

            except httpx.HTTPError as e:
                logger.error(f"Erro HTTP ao criar instância: {e}")
                raise

    async def get_connection_state(self, tenant_id: str) -> Dict[str, Any]:
        """
        Verifica o estado da conexão da instância.
        Retorna: {"state": "open"} ou {"state": "close"}
        """
        instance_name = self._get_instance_name(tenant_id)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/instance/connectionState/{instance_name}",
                    headers=self.headers
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "instance": instance_name,
                        "state": data.get("state", "unknown"),
                        "connected": data.get("state") == "open"
                    }
                elif response.status_code == 404:
                    return {
                        "instance": instance_name,
                        "state": "not_found",
                        "connected": False
                    }

                response.raise_for_status()

            except httpx.HTTPError as e:
                logger.error(f"Erro ao verificar conexão: {e}")
                return {
                    "instance": instance_name,
                    "state": "error",
                    "connected": False,
                    "error": str(e)
                }

    async def get_qrcode(self, tenant_id: str) -> Dict[str, Any]:
        """
        Obtém o QR Code para conexão.
        Retorna base64 da imagem e pairing code.
        """
        instance_name = self._get_instance_name(tenant_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/instance/connect/{instance_name}",
                    headers=self.headers
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "instance": instance_name,
                        "base64": data.get("base64"),
                        "pairingCode": data.get("pairingCode"),
                        "code": data.get("code")
                    }

                response.raise_for_status()

            except httpx.HTTPError as e:
                logger.error(f"Erro ao obter QR Code: {e}")
                raise

    async def logout(self, tenant_id: str) -> Dict[str, Any]:
        """Desconecta a instância (logout do WhatsApp)."""
        instance_name = self._get_instance_name(tenant_id)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/instance/logout/{instance_name}",
                    headers=self.headers
                )

                return {
                    "instance": instance_name,
                    "status": "logged_out" if response.status_code == 200 else "error"
                }

            except httpx.HTTPError as e:
                logger.error(f"Erro ao fazer logout: {e}")
                raise

    async def delete_instance(self, tenant_id: str) -> Dict[str, Any]:
        """Remove completamente a instância."""
        instance_name = self._get_instance_name(tenant_id)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/instance/delete/{instance_name}",
                    headers=self.headers
                )

                return {
                    "instance": instance_name,
                    "status": "deleted" if response.status_code == 200 else "error"
                }

            except httpx.HTTPError as e:
                logger.error(f"Erro ao deletar instância: {e}")
                raise

    async def restart_instance(self, tenant_id: str) -> Dict[str, Any]:
        """Reinicia a instância."""
        instance_name = self._get_instance_name(tenant_id)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.put(
                    f"{self.base_url}/instance/restart/{instance_name}",
                    headers=self.headers
                )

                return {
                    "instance": instance_name,
                    "status": "restarted" if response.status_code == 200 else "error"
                }

            except httpx.HTTPError as e:
                logger.error(f"Erro ao reiniciar: {e}")
                raise

    async def get_instance_info(self, tenant_id: str) -> Dict[str, Any]:
        """Obtém informações detalhadas da instância."""
        instance_name = self._get_instance_name(tenant_id)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/instance/fetchInstances",
                    headers=self.headers,
                    params={"instanceName": instance_name}
                )

                if response.status_code == 200:
                    data = response.json()
                    instances = data if isinstance(data, list) else [data]

                    for inst in instances:
                        if inst.get("instance", {}).get("instanceName") == instance_name:
                            return {
                                "instance": instance_name,
                                "exists": True,
                                "data": inst
                            }

                    return {"instance": instance_name, "exists": False}

                return {"instance": instance_name, "exists": False}

            except httpx.HTTPError as e:
                logger.error(f"Erro ao buscar info: {e}")
                return {"instance": instance_name, "exists": False, "error": str(e)}

    async def send_text_message(
        self,
        tenant_id: str,
        phone_number: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Envia mensagem de texto via WhatsApp.

        Args:
            tenant_id: ID do tenant
            phone_number: Número no formato 5541999999999
            message: Texto da mensagem
        """
        instance_name = self._get_instance_name(tenant_id)

        payload = {
            "number": phone_number,
            "text": message
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/message/sendText/{instance_name}",
                    json=payload,
                    headers=self.headers
                )

                if response.status_code == 200:
                    return response.json()

                logger.error(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
                response.raise_for_status()

            except httpx.HTTPError as e:
                logger.error(f"Erro HTTP ao enviar mensagem: {e}")
                raise


# Instância singleton
evolution_client = EvolutionAPIClient()

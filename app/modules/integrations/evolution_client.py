"""
Cliente HTTP para comunicação com a Evolution API.

Documentação: https://doc.evolution-api.com/

USO:
    from app.modules.integrations.evolution_client import evolution_client

    result = await evolution_client.get_connection_state("tenant-uuid")
"""
import httpx
from typing import Dict, Any, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EvolutionAPIClient:
    """
    Cliente HTTP para comunicação com a Evolution API.
    Cada tenant tem sua própria instância identificada por tenant_UUID.
    """

    def __init__(self):
        self.base_url = (settings.EVOLUTION_API_URL or "").rstrip('/')
        self.api_key = settings.EVOLUTION_API_KEY or ""
        self.webhook_url = settings.EVOLUTION_WEBHOOK_URL or ""
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

        # Validação inicial
        if not self.base_url:
            logger.warning("EVOLUTION_API_URL não configurada!")
        if not self.api_key:
            logger.warning("EVOLUTION_API_KEY não configurada!")

    def _get_instance_name(self, tenant_id: str) -> str:
        """Gera nome único da instância baseado no tenant_id."""
        return f"tenant_{tenant_id}"

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Método auxiliar para fazer requisições com tratamento de erro."""

        if not self.base_url:
            raise Exception("EVOLUTION_API_URL não configurada. Verifique o arquivo .env")

        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=self.headers)
                elif method == "POST":
                    response = await client.post(url, json=json_data, headers=self.headers)
                elif method == "PUT":
                    response = await client.put(url, json=json_data, headers=self.headers)
                elif method == "DELETE":
                    response = await client.delete(url, headers=self.headers)
                else:
                    raise ValueError(f"Método HTTP não suportado: {method}")

                # Log para debug
                logger.debug(f"[Evolution] {method} {url} -> {response.status_code}")

                return {
                    "status_code": response.status_code,
                    "data": response.json() if response.content else {},
                    "success": response.status_code in [200, 201, 204]
                }

            except httpx.ConnectError as e:
                logger.error(f"[Evolution] Erro de conexão: {e}")
                raise Exception(
                    f"Não foi possível conectar à Evolution API em {self.base_url}. "
                    f"Verifique se o serviço está rodando e a URL está correta."
                )
            except httpx.TimeoutException as e:
                logger.error(f"[Evolution] Timeout: {e}")
                raise Exception("Timeout ao conectar com Evolution API")
            except Exception as e:
                logger.error(f"[Evolution] Erro: {e}")
                raise

    async def check_connection(self) -> bool:
        """Verifica se a Evolution API está acessível."""
        try:
            result = await self._make_request("GET", "/instance/fetchInstances")
            return result["success"]
        except Exception:
            return False

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

        result = await self._make_request("POST", "/instance/create", payload)

        # Se já existe (409), não é erro
        if result["status_code"] in [200, 201, 409]:
            logger.info(f"Instância criada/existente: {instance_name}")
            return {"instance": instance_name, "status": "ok"}

        raise Exception(f"Erro ao criar instância: {result['data']}")

    async def get_connection_state(self, tenant_id: str) -> Dict[str, Any]:
        """
        Verifica o estado da conexão da instância.
        Retorna: {"state": "open"} ou {"state": "close"}
        """
        instance_name = self._get_instance_name(tenant_id)

        try:
            result = await self._make_request(
                "GET",
                f"/instance/connectionState/{instance_name}",
                timeout=10.0
            )

            if result["success"]:
                state = result["data"].get("state", "unknown")
                return {
                    "instance": instance_name,
                    "state": state,
                    "connected": state == "open"
                }
            elif result["status_code"] == 404:
                return {
                    "instance": instance_name,
                    "state": "not_found",
                    "connected": False
                }

            return {
                "instance": instance_name,
                "state": "error",
                "connected": False
            }

        except Exception as e:
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

        result = await self._make_request("GET", f"/instance/connect/{instance_name}")

        if result["success"]:
            data = result["data"]
            return {
                "instance": instance_name,
                "base64": data.get("base64"),
                "pairingCode": data.get("pairingCode"),
                "code": data.get("code")
            }

        raise Exception(f"Erro ao obter QR Code: {result['data']}")

    async def logout(self, tenant_id: str) -> Dict[str, Any]:
        """Desconecta a instância (logout do WhatsApp)."""
        instance_name = self._get_instance_name(tenant_id)

        result = await self._make_request(
            "DELETE",
            f"/instance/logout/{instance_name}",
            timeout=10.0
        )

        return {
            "instance": instance_name,
            "status": "logged_out" if result["success"] else "error"
        }

    async def delete_instance(self, tenant_id: str) -> Dict[str, Any]:
        """Remove completamente a instância."""
        instance_name = self._get_instance_name(tenant_id)

        result = await self._make_request(
            "DELETE",
            f"/instance/delete/{instance_name}",
            timeout=10.0
        )

        return {
            "instance": instance_name,
            "status": "deleted" if result["success"] else "error"
        }

    async def restart_instance(self, tenant_id: str) -> Dict[str, Any]:
        """Reinicia a instância."""
        instance_name = self._get_instance_name(tenant_id)

        result = await self._make_request(
            "PUT",
            f"/instance/restart/{instance_name}",
            timeout=10.0
        )

        return {
            "instance": instance_name,
            "status": "restarted" if result["success"] else "error"
        }

    async def get_instance_info(self, tenant_id: str) -> Dict[str, Any]:
        """Obtém informações detalhadas da instância."""
        instance_name = self._get_instance_name(tenant_id)

        try:
            result = await self._make_request(
                "GET",
                f"/instance/fetchInstances",
                timeout=10.0
            )

            if result["success"]:
                data = result["data"]
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

        except Exception as e:
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

        result = await self._make_request(
            "POST",
            f"/message/sendText/{instance_name}",
            payload
        )

        if result["success"]:
            return result["data"]

        raise Exception(f"Erro ao enviar mensagem: {result['data']}")


# Instância singleton
evolution_client = EvolutionAPIClient()
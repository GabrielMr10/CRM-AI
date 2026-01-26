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
        Se já existir (erro 403 ou 409), ignora e retorna sucesso.
        """
        instance_name = self._get_instance_name(tenant_id)

        payload = {
            "instanceName": instance_name,
            "token": tenant_id,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
            "webhook": {
                "url": self.webhook_url,
                "byEvents": False,
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

        try:
            result = await self._make_request("POST", "/instance/create", payload)

            if result["status_code"] in [200, 201]:
                logger.info(f"Instância criada: {instance_name}")
                return {"instance": instance_name, "status": "created"}

            # 403 = já existe (Forbidden - "already in use")
            if result["status_code"] == 403:
                error_msg = str(result.get("data", {}))
                if "already in use" in error_msg.lower():
                    logger.info(f"Instância já existe (403): {instance_name}")
                    return {"instance": instance_name, "status": "exists"}

            # 409 = conflito, também significa que já existe
            if result["status_code"] == 409:
                logger.info(f"Instância já existe (409): {instance_name}")
                return {"instance": instance_name, "status": "exists"}

            # Outros erros
            raise Exception(f"Erro ao criar instância: {result['data']}")

        except Exception as e:
            error_str = str(e).lower()
            # Trata caso o erro venha como exceção
            if "already in use" in error_str or "403" in error_str:
                logger.info(f"Instância já existe (exception): {instance_name}")
                return {"instance": instance_name, "status": "exists"}
            raise

    async def get_connection_state(self, tenant_id: str) -> Dict[str, Any]:
        """
        Verifica o estado da conexão da instância.
        Tenta múltiplos endpoints para garantir resposta correta.
        """
        instance_name = self._get_instance_name(tenant_id)

        # Primeiro tenta o endpoint connectionState
        try:
            result = await self._make_request(
                "GET",
                f"/instance/connectionState/{instance_name}",
                timeout=10.0
            )

            print(f"👀 connectionState response: {result}")

            if result["success"]:
                data = result["data"]
                state = data.get("state", "unknown")

                # Se estado é "unknown", tenta endpoint alternativo
                if state == "unknown":
                    return await self._get_instance_info_fallback(instance_name)

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

        except Exception as e:
            print(f"❌ Erro connectionState: {e}")

        # Fallback: buscar info da instância
        return await self._get_instance_info_fallback(instance_name)

    async def _get_instance_info_fallback(self, instance_name: str) -> Dict[str, Any]:
        """
        Fallback: busca informações detalhadas da instância
        para determinar se está conectada.
        """
        try:
            result = await self._make_request(
                "GET",
                f"/instance/fetchInstances",
                timeout=10.0
            )

            print(f"👀 fetchInstances response: {result}")

            if result["success"]:
                data = result["data"]
                instances = data if isinstance(data, list) else [data]

                for inst in instances:
                    if isinstance(inst, dict):
                        # Tenta pegar o nome da instância
                        inst_name = (
                            inst.get("instanceName") or
                            inst.get("instance", {}).get("instanceName") if isinstance(inst.get("instance"), dict) else None or
                            inst.get("name")
                        )

                        # Tenta pegar o estado
                        inst_state = (
                            inst.get("state") or
                            (inst.get("instance", {}).get("state") if isinstance(inst.get("instance"), dict) else None) or
                            inst.get("connectionStatus") or
                            inst.get("status") or
                            "unknown"
                        )

                        # Verifica campo específico de conexão
                        if inst.get("connected") is True:
                            inst_state = "open"
                        elif isinstance(inst.get("instance"), dict) and inst.get("instance", {}).get("status") == "open":
                            inst_state = "open"

                        if inst_name == instance_name:
                            inst_state = str(inst_state).lower()
                            is_connected = inst_state in ["open", "connected", "online"]

                            return {
                                "instance": instance_name,
                                "state": "open" if is_connected else inst_state,
                                "connected": is_connected
                            }

            return {
                "instance": instance_name,
                "state": "close",
                "connected": False
            }

        except Exception as e:
            print(f"❌ Erro fetchInstances: {e}")
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

    async def get_media_base64(
        self,
        tenant_id: str,
        message_id: str,
    ) -> Dict[str, Any]:
        """
        Obtém mídia de uma mensagem em base64.

        Endpoint: POST /chat/getBase64FromMediaMessage/{instance}
        """
        instance_name = self._get_instance_name(tenant_id)

        payload = {
            "message": {
                "key": {
                    "id": message_id
                }
            },
            "convertToMp4": False
        }

        try:
            result = await self._make_request(
                "POST",
                f"/chat/getBase64FromMediaMessage/{instance_name}",
                payload,
                timeout=60.0
            )

            if result["success"]:
                return result["data"]

            logger.warning(f"Falha ao obter mídia: {result}")
            return {}

        except Exception as e:
            logger.error(f"Erro ao obter mídia: {e}")
            return {}

    async def get_profile_picture(
        self,
        tenant_id: str,
        phone_number: str,
    ) -> Optional[str]:
        """
        Obtém a foto de perfil de um contato do WhatsApp.

        Endpoint: GET /chat/fetchProfilePictureUrl/{instance}?number={phone}
        """
        instance_name = self._get_instance_name(tenant_id)

        try:
            result = await self._make_request(
                "GET",
                f"/chat/fetchProfilePictureUrl/{instance_name}?number={phone_number}",
                timeout=15.0
            )

            if result["success"]:
                data = result["data"]
                picture_url = data.get("profilePictureUrl") or data.get("picture") or data.get("url")
                if picture_url and picture_url != "null":
                    return picture_url

            return None

        except Exception as e:
            logger.debug(f"Não foi possível obter foto de perfil de {phone_number}: {e}")
            return None


# Instância singleton
evolution_client = EvolutionAPIClient()
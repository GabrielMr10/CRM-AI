"""
Gerenciador de conexões WebSocket.

Permite comunicação em tempo real entre backend e frontend.
Organiza conexões por tenant e usuário.

USO:
    from app.core.websocket_manager import ws_manager

    # Notificar nova mensagem
    await ws_manager.broadcast_new_message(
        tenant_id="uuid",
        conversation_id="uuid",
        message={"id": "...", "content": "..."}
    )
"""
from fastapi import WebSocket
from typing import Dict, Set, Optional
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gerencia conexões WebSocket por tenant e usuário.
    Permite enviar mensagens em tempo real para usuários específicos ou todos de um tenant.
    """

    def __init__(self):
        # Estrutura: {tenant_id: {user_id: {websocket1, websocket2, ...}}}
        self.active_connections: Dict[str, Dict[str, Set[WebSocket]]] = {}

        # Conexões por conversa: {conversation_id: {websocket1, websocket2, ...}}
        self.conversation_subscribers: Dict[str, Set[WebSocket]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        tenant_id: str,
        user_id: str
    ):
        """Aceita e registra uma nova conexão WebSocket."""
        await websocket.accept()

        # Inicializa estruturas se necessário
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = {}

        if user_id not in self.active_connections[tenant_id]:
            self.active_connections[tenant_id][user_id] = set()

        self.active_connections[tenant_id][user_id].add(websocket)

        logger.info(f"WebSocket conectado: tenant={tenant_id}, user={user_id}")

        # Envia confirmação de conexão
        await websocket.send_json({
            "type": "connection_established",
            "message": "Conectado ao CRM em tempo real"
        })

    def disconnect(self, websocket: WebSocket, tenant_id: str, user_id: str):
        """Remove uma conexão WebSocket."""
        try:
            if tenant_id in self.active_connections:
                if user_id in self.active_connections[tenant_id]:
                    self.active_connections[tenant_id][user_id].discard(websocket)

                    # Limpa estruturas vazias
                    if not self.active_connections[tenant_id][user_id]:
                        del self.active_connections[tenant_id][user_id]
                    if not self.active_connections[tenant_id]:
                        del self.active_connections[tenant_id]

            # Remove de todas as assinaturas de conversa
            for conv_id in list(self.conversation_subscribers.keys()):
                self.conversation_subscribers[conv_id].discard(websocket)
                if not self.conversation_subscribers[conv_id]:
                    del self.conversation_subscribers[conv_id]

            logger.info(f"WebSocket desconectado: tenant={tenant_id}, user={user_id}")
        except Exception as e:
            logger.error(f"Erro ao desconectar WebSocket: {e}")

    def subscribe_to_conversation(self, websocket: WebSocket, conversation_id: str):
        """Inscreve um WebSocket para receber atualizações de uma conversa específica."""
        if conversation_id not in self.conversation_subscribers:
            self.conversation_subscribers[conversation_id] = set()
        self.conversation_subscribers[conversation_id].add(websocket)
        logger.debug(f"WebSocket inscrito na conversa {conversation_id}")

    def unsubscribe_from_conversation(self, websocket: WebSocket, conversation_id: str):
        """Remove inscrição de uma conversa."""
        if conversation_id in self.conversation_subscribers:
            self.conversation_subscribers[conversation_id].discard(websocket)

    async def send_to_user(self, tenant_id: str, user_id: str, data: dict):
        """Envia mensagem para um usuário específico (todas as abas/dispositivos)."""
        if tenant_id in self.active_connections:
            if user_id in self.active_connections[tenant_id]:
                dead_connections = set()
                for websocket in self.active_connections[tenant_id][user_id]:
                    try:
                        await websocket.send_json(data)
                    except Exception as e:
                        logger.error(f"Erro ao enviar para usuário {user_id}: {e}")
                        dead_connections.add(websocket)

                # Remove conexões mortas
                for ws in dead_connections:
                    self.active_connections[tenant_id][user_id].discard(ws)

    async def send_to_tenant(self, tenant_id: str, data: dict):
        """Envia mensagem para todos os usuários de um tenant."""
        if tenant_id in self.active_connections:
            for user_id in self.active_connections[tenant_id]:
                await self.send_to_user(tenant_id, user_id, data)

    async def send_to_conversation_subscribers(self, conversation_id: str, data: dict):
        """Envia mensagem para todos inscritos em uma conversa."""
        if conversation_id in self.conversation_subscribers:
            dead_connections = set()
            for websocket in self.conversation_subscribers[conversation_id]:
                try:
                    await websocket.send_json(data)
                except Exception as e:
                    logger.error(f"Erro ao enviar para conversa {conversation_id}: {e}")
                    dead_connections.add(websocket)

            # Remove conexões mortas
            for ws in dead_connections:
                self.conversation_subscribers[conversation_id].discard(ws)

    async def broadcast_new_message(
        self,
        tenant_id: str,
        conversation_id: str,
        message: dict
    ):
        """
        Notifica sobre nova mensagem.
        Envia para todos do tenant (para atualizar lista) e para inscritos na conversa.
        """
        # Evento para atualizar lista de conversas (todos do tenant)
        await self.send_to_tenant(tenant_id, {
            "type": "conversation_updated",
            "conversation_id": conversation_id,
            "last_message": message.get("content", ""),
            "last_message_at": message.get("created_at"),
            "unread_count_increment": 1 if message.get("direction") == "inbound" else 0
        })

        # Evento com mensagem completa (para quem está na conversa)
        await self.send_to_conversation_subscribers(conversation_id, {
            "type": "new_message",
            "conversation_id": conversation_id,
            "message": message
        })

    async def broadcast_message_status(
        self,
        tenant_id: str,
        conversation_id: str,
        message_id: str,
        status: str
    ):
        """Notifica sobre mudança de status de mensagem (sent, delivered, read)."""
        payload = {
            "type": "message_status_updated",
            "conversation_id": conversation_id,
            "message_id": message_id,
            "status": status
        }
        print(f"📤 [WebSocket] Enviando status update: {payload}")

        # Envia para inscritos na conversa
        await self.send_to_conversation_subscribers(conversation_id, payload)

        # Também envia para todo o tenant (garante que chegue mesmo se não inscrito)
        await self.send_to_tenant(tenant_id, payload)

    async def broadcast_conversation_assigned(
        self,
        tenant_id: str,
        conversation_id: str,
        assigned_to_id: str,
        assigned_to_name: str
    ):
        """Notifica quando conversa é atribuída a um usuário."""
        await self.send_to_tenant(tenant_id, {
            "type": "conversation_assigned",
            "conversation_id": conversation_id,
            "assigned_to_id": assigned_to_id,
            "assigned_to_name": assigned_to_name
        })

    async def broadcast_typing(
        self,
        conversation_id: str,
        user_id: str,
        user_name: str
    ):
        """Notifica que um usuário está digitando."""
        await self.send_to_conversation_subscribers(conversation_id, {
            "type": "user_typing",
            "conversation_id": conversation_id,
            "user_id": user_id,
            "user_name": user_name
        })

    async def broadcast_appointment_created(
        self,
        tenant_id: str,
        appointment: dict
    ):
        """Notifica sobre novo agendamento."""
        await self.send_to_tenant(tenant_id, {
            "type": "appointment_created",
            "appointment": appointment
        })

    async def broadcast_appointment_updated(
        self,
        tenant_id: str,
        appointment: dict
    ):
        """Notifica sobre agendamento atualizado."""
        await self.send_to_tenant(tenant_id, {
            "type": "appointment_updated",
            "appointment": appointment
        })

    async def broadcast_lead_created(
        self,
        tenant_id: str,
        lead: dict
    ):
        """Notifica sobre novo lead."""
        await self.send_to_tenant(tenant_id, {
            "type": "lead_created",
            "lead": lead
        })

    def get_connection_count(self, tenant_id: Optional[str] = None) -> int:
        """Retorna número de conexões ativas."""
        if tenant_id:
            if tenant_id in self.active_connections:
                return sum(
                    len(connections)
                    for connections in self.active_connections[tenant_id].values()
                )
            return 0

        return sum(
            len(connections)
            for tenant in self.active_connections.values()
            for connections in tenant.values()
        )

    def get_stats(self) -> dict:
        """Retorna estatísticas das conexões."""
        return {
            "total_connections": self.get_connection_count(),
            "tenants_connected": len(self.active_connections),
            "conversations_with_subscribers": len(self.conversation_subscribers),
            "connections_by_tenant": {
                tenant_id: self.get_connection_count(tenant_id)
                for tenant_id in self.active_connections
            }
        }


# Instância global (singleton)
ws_manager = ConnectionManager()
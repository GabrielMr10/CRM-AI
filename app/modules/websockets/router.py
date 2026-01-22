"""
Router - Endpoints WebSocket.

Conexão: ws://localhost:8000/api/v1/ws?token=JWT_TOKEN

USO:
    from app.modules.websockets.router import router as websocket_router
    app.include_router(websocket_router, prefix="/api/v1", tags=["WebSocket"])
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import json
import logging

from jose import JWTError

from app.core.websocket_manager import ws_manager
from app.core.security import decode_token
from .events import WebSocketEventType

logger = logging.getLogger(__name__)

router = APIRouter()


def get_user_from_token(token: str) -> dict | None:
    """
    Valida token JWT e retorna dados do usuário.

    Args:
        token: JWT token

    Returns:
        Dict com user_id e tenant_id ou None se inválido
    """
    try:
        payload = decode_token(token)
        if not payload:
            return None

        # Verifica se é token de acesso (não refresh)
        if payload.get("type") != "access":
            return None

        return {
            "user_id": payload.get("sub"),
            "tenant_id": payload.get("tenant_id")
        }
    except JWTError as e:
        logger.error(f"Erro ao validar token WebSocket: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao validar token WebSocket: {e}")
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT Token para autenticação")
):
    """
    Endpoint WebSocket principal.

    Conexão: ws://localhost:8000/api/v1/ws?token=JWT_TOKEN

    Eventos que o cliente pode enviar:
    - {"type": "subscribe_conversation", "conversation_id": "uuid"}
    - {"type": "unsubscribe_conversation", "conversation_id": "uuid"}
    - {"type": "mark_as_read", "conversation_id": "uuid"}
    - {"type": "typing", "conversation_id": "uuid"}
    - {"type": "ping"}

    Eventos que o servidor envia:
    - {"type": "connection_established", "message": "..."}
    - {"type": "new_message", "conversation_id": "uuid", "message": {...}}
    - {"type": "conversation_updated", "conversation_id": "uuid", ...}
    - {"type": "message_status_updated", "conversation_id": "uuid", "message_id": "uuid", "status": "read"}
    - {"type": "appointment_created", "appointment": {...}}
    - {"type": "lead_created", "lead": {...}}
    - {"type": "pong"}
    """
    # Valida token antes de aceitar conexão
    user_data = get_user_from_token(token)

    if not user_data:
        await websocket.close(code=4001, reason="Token inválido ou expirado")
        return

    tenant_id = user_data["tenant_id"]
    user_id = user_data["user_id"]

    # Conecta
    await ws_manager.connect(websocket, tenant_id, user_id)

    try:
        while True:
            # Aguarda mensagem do cliente
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                event_type = message.get("type")

                # ==================== PING/PONG ====================
                if event_type == WebSocketEventType.PING:
                    await websocket.send_json({"type": WebSocketEventType.PONG})

                # ==================== INSCRIÇÃO EM CONVERSA ====================
                elif event_type == WebSocketEventType.SUBSCRIBE_CONVERSATION:
                    conversation_id = message.get("conversation_id")
                    if conversation_id:
                        ws_manager.subscribe_to_conversation(websocket, conversation_id)
                        await websocket.send_json({
                            "type": WebSocketEventType.SUBSCRIBED,
                            "conversation_id": conversation_id
                        })
                    else:
                        await websocket.send_json({
                            "type": WebSocketEventType.ERROR,
                            "message": "conversation_id é obrigatório"
                        })

                # ==================== CANCELAR INSCRIÇÃO ====================
                elif event_type == WebSocketEventType.UNSUBSCRIBE_CONVERSATION:
                    conversation_id = message.get("conversation_id")
                    if conversation_id:
                        ws_manager.unsubscribe_from_conversation(websocket, conversation_id)
                        await websocket.send_json({
                            "type": WebSocketEventType.UNSUBSCRIBED,
                            "conversation_id": conversation_id
                        })

                # ==================== MARCAR COMO LIDO ====================
                elif event_type == WebSocketEventType.MARK_AS_READ:
                    conversation_id = message.get("conversation_id")
                    if conversation_id:
                        # Notifica outros usuários do tenant
                        await ws_manager.send_to_tenant(tenant_id, {
                            "type": WebSocketEventType.MESSAGES_READ,
                            "conversation_id": conversation_id,
                            "read_by": user_id
                        })

                # ==================== DIGITANDO ====================
                elif event_type == WebSocketEventType.TYPING:
                    conversation_id = message.get("conversation_id")
                    if conversation_id:
                        # Notifica outros usuários inscritos na conversa
                        await ws_manager.send_to_conversation_subscribers(conversation_id, {
                            "type": WebSocketEventType.USER_TYPING,
                            "conversation_id": conversation_id,
                            "user_id": user_id
                        })

                else:
                    logger.warning(f"Evento desconhecido: {event_type}")
                    await websocket.send_json({
                        "type": WebSocketEventType.ERROR,
                        "message": f"Evento desconhecido: {event_type}"
                    })

            except json.JSONDecodeError:
                logger.error(f"JSON inválido recebido: {data}")
                await websocket.send_json({
                    "type": WebSocketEventType.ERROR,
                    "message": "JSON inválido"
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, tenant_id, user_id)
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")
        ws_manager.disconnect(websocket, tenant_id, user_id)


@router.get("/ws/stats", summary="Estatísticas WebSocket")
async def websocket_stats():
    """
    Retorna estatísticas das conexões WebSocket ativas.

    Returns:
        Contagem de conexões por tenant e total
    """
    return ws_manager.get_stats()


@router.get("/ws/health", summary="Health check WebSocket")
async def websocket_health():
    """
    Health check do sistema WebSocket.

    Returns:
        Status do WebSocket manager
    """
    return {
        "status": "healthy",
        "total_connections": ws_manager.get_connection_count()
    }
"""
Router - Endpoints HTTP do módulo Conversations.
"""
import uuid
from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.modules.conversations.schemas import (
    ConversationResponse,
    ConversationListResponse,
    ConversationWithMessages,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
)
from app.modules.conversations.service import ConversationService
from app.modules.tenants.dependencies import CurrentTenant
from app.modules.users.models import User

router = APIRouter()


# ==================== CONVERSATIONS ====================

@router.get(
    "/",
    response_model=ConversationListResponse,
    summary="Listar conversas",
)
def list_conversations(
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    is_unread: bool | None = None,
    assigned_to_id: uuid.UUID | None = None,
    search: str | None = None,
):
    """Lista conversas do tenant."""
    return ConversationService.list_paginated(
        db,
        tenant.id,
        page=page,
        per_page=per_page,
        is_unread=is_unread,
        assigned_to_id=assigned_to_id,
        search=search,
    )


@router.get(
    "/stats",
    summary="Estatísticas de conversas",
)
def get_conversation_stats(
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna estatísticas para dashboard."""
    return ConversationService.get_stats(db, tenant.id)


@router.get(
    "/by-phone/{phone}",
    response_model=ConversationResponse | None,
    summary="Buscar por telefone",
)
def get_conversation_by_phone(
    phone: str,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca conversa pelo telefone."""
    return ConversationService.get_by_phone(db, phone, tenant.id)


@router.get(
    "/{conversation_id}",
    response_model=ConversationWithMessages,
    summary="Detalhe da conversa",
)
def get_conversation(
    conversation_id: uuid.UUID,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    messages_limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """Retorna conversa com mensagens."""
    return ConversationService.get_with_messages(
        db, conversation_id, tenant.id, messages_limit=messages_limit
    )


@router.get(
    "/{conversation_id}/messages",
    response_model=MessageListResponse,
    summary="Carregar mais mensagens",
)
def get_messages(
    conversation_id: uuid.UUID,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    before: datetime | None = None,
):
    """Carrega mensagens anteriores (paginação infinita)."""
    return ConversationService.get_messages(
        db, conversation_id, tenant.id, limit=limit, before=before
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar mensagem",
)
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Envia mensagem via WhatsApp (Evolution API) e salva no histórico.
    """
    from app.modules.integrations.evolution_client import evolution_client

    # 1. Busca a conversa para obter o telefone
    conversation = ConversationService.get_or_404(db, conversation_id, tenant.id)

    # 2. Envia para o WhatsApp via Evolution API
    external_id = None
    send_success = False
    try:
        evolution_result = await evolution_client.send_text_message(
            tenant_id=str(tenant.id),
            phone_number=conversation.phone,
            message=data.content
        )
        external_id = evolution_result.get("key", {}).get("id")
        send_success = True
        print(f"✅ [WhatsApp] Mensagem enviada: {external_id}")
    except Exception as e:
        print(f"❌ [WhatsApp] Erro ao enviar: {e}")
        import traceback
        traceback.print_exc()
        # Não falha o endpoint - ainda salva a mensagem localmente

    # 3. Salva a mensagem no banco de dados
    # Se Evolution API confirmou envio, já salva como "sent"
    from app.modules.conversations.models import MessageStatus
    initial_status = MessageStatus.SENT.value if send_success else MessageStatus.PENDING.value

    message = ConversationService.send_message(
        db,
        conversation_id=conversation_id,
        tenant_id=tenant.id,
        data=data,
        sent_by=current_user,
        external_id=external_id,
        status=initial_status,
    )

    return message


@router.post(
    "/{conversation_id}/read",
    response_model=ConversationResponse,
    summary="Marcar como lida",
)
def mark_as_read(
    conversation_id: uuid.UUID,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca conversa como lida."""
    return ConversationService.mark_as_read(
        db, conversation_id=conversation_id, tenant_id=tenant.id
    )


@router.post(
    "/{conversation_id}/toggle-bot",
    response_model=ConversationResponse,
    summary="Ativar/desativar bot",
)
def toggle_bot(
    conversation_id: uuid.UUID,
    is_active: bool,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ativa ou desativa o bot (Laura) nesta conversa."""
    return ConversationService.toggle_bot(
        db, conversation_id=conversation_id, tenant_id=tenant.id, is_active=is_active
    )


@router.patch(
    "/{conversation_id}/assign",
    response_model=ConversationResponse,
    summary="Atribuir atendente",
)
def assign_conversation(
    conversation_id: uuid.UUID,
    tenant: CurrentTenant,
    user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atribui conversa a um atendente."""
    return ConversationService.assign(
        db, conversation_id=conversation_id, tenant_id=tenant.id, user_id=user_id
    )


@router.patch(
    "/{conversation_id}/link-lead/{lead_id}",
    response_model=ConversationResponse,
    summary="Vincular a lead",
)
def link_lead(
    conversation_id: uuid.UUID,
    lead_id: uuid.UUID,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vincula conversa a um lead."""
    return ConversationService.link_lead(
        db, conversation_id=conversation_id, tenant_id=tenant.id, lead_id=lead_id
    )
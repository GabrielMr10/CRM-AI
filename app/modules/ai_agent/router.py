"""
Router do AI Agent.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.modules.ai_agent.schemas import (
    AgentConfigUpdate,
    AgentConfigResponse,
    AgentStatusResponse,
    AgentPromptRequest,
    AgentPromptResponse,
)
from app.modules.ai_agent.service import AgentConfigService
from app.modules.tenants.dependencies import CurrentTenant
from app.modules.users.models import User

router = APIRouter()


# ==================== CONFIG (CRM UI) ====================

@router.get(
    "/config",
    response_model=AgentConfigResponse,
    summary="Obter configuração",
)
def get_config(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Retorna configuração do agente."""
    config = AgentConfigService.get_or_create(db, tenant.id)
    return AgentConfigService.to_response(config)


@router.patch(
    "/config",
    response_model=AgentConfigResponse,
    summary="Atualizar configuração",
)
def update_config(
    data: AgentConfigUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Atualiza configuração do agente."""
    config = AgentConfigService.update(db, tenant_id=tenant.id, data=data)
    return AgentConfigService.to_response(config)


@router.post(
    "/toggle",
    response_model=AgentConfigResponse,
    summary="Ativar/desativar agente",
)
def toggle_agent(
    is_enabled: bool,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Liga/desliga o agente globalmente."""
    config = AgentConfigService.toggle(db, tenant_id=tenant.id, is_enabled=is_enabled)
    return AgentConfigService.to_response(config)


@router.get(
    "/status",
    response_model=AgentStatusResponse,
    summary="Status do agente",
)
def get_status(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Retorna status resumido (ativo, dentro do horário, etc)."""
    return AgentConfigService.get_status(db, tenant.id)


# ==================== PROMPT (PARA N8N) ====================

@router.post(
    "/prompt",
    response_model=AgentPromptResponse,
    summary="Obter prompt para n8n",
)
def get_prompt(
    request: AgentPromptRequest,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
):
    """
    Endpoint para n8n obter prompt montado.
    
    O n8n chama este endpoint antes de enviar para a IA.
    Retorna:
    - should_respond: Se deve responder ou não
    - system_prompt: Prompt completo montado
    - llm_config: Configurações do modelo
    """
    return AgentConfigService.get_prompt_for_n8n(
        db,
        tenant_id=tenant.id,
        request=request,
    )


# ==================== ENDPOINT PÚBLICO PARA N8N (sem auth) ====================

@router.post(
    "/prompt/{tenant_id}",
    response_model=AgentPromptResponse,
    summary="Obter prompt (público)",
    description="Endpoint sem autenticação para n8n usar",
)
def get_prompt_public(
    tenant_id: str,
    request: AgentPromptRequest,
    db: Session = Depends(get_db),
):
    """
    Endpoint público para n8n obter prompt.
    
    URL: POST /api/v1/ai-agent/prompt/{tenant_id}
    
    Não requer autenticação JWT, apenas o tenant_id na URL.
    Use em workflows n8n que não têm token de usuário.
    """
    from uuid import UUID
    
    try:
        tenant_uuid = UUID(tenant_id)
    except ValueError:
        from app.modules.ai_agent.exceptions import AgentConfigNotFoundError
        raise AgentConfigNotFoundError(tenant_id)
    
    return AgentConfigService.get_prompt_for_n8n(
        db,
        tenant_id=tenant_uuid,
        request=request,
    )
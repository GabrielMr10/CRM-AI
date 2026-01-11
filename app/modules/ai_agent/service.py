"""
Service do AI Agent.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.ai_agent.models import AgentConfig
from app.modules.ai_agent.schemas import (
    AgentConfigUpdate,
    AgentConfigResponse,
    AgentStatusResponse,
    AgentPromptRequest,
    AgentPromptResponse,
    LLMConfig,
)
from app.modules.ai_agent.repository import AgentConfigRepository
from app.modules.ai_agent.exceptions import AgentConfigNotFoundError


class AgentConfigService:
    
    @staticmethod
    def get_or_create(db: Session, tenant_id: uuid.UUID) -> AgentConfig:
        """Obtém config ou cria default."""
        config, _ = AgentConfigRepository.get_or_create(db, tenant_id=tenant_id)
        return config
    
    @staticmethod
    def get_or_404(db: Session, tenant_id: uuid.UUID) -> AgentConfig:
        config = AgentConfigRepository.get_by_tenant(db, tenant_id)
        if not config:
            raise AgentConfigNotFoundError(str(tenant_id))
        return config
    
    @staticmethod
    def update(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        data: AgentConfigUpdate,
    ) -> AgentConfig:
        config = AgentConfigService.get_or_create(db, tenant_id)
        return AgentConfigRepository.update(db, config=config, data=data)
    
    @staticmethod
    def toggle(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        is_enabled: bool,
    ) -> AgentConfig:
        config = AgentConfigService.get_or_create(db, tenant_id)
        return AgentConfigRepository.toggle(db, config=config, is_enabled=is_enabled)
    
    @staticmethod
    def get_status(db: Session, tenant_id: uuid.UUID) -> AgentStatusResponse:
        config = AgentConfigService.get_or_create(db, tenant_id)
        
        is_within = config.is_within_schedule(datetime.now(timezone.utc))
        
        schedule_str = None
        if config.schedule_enabled and config.schedule_start and config.schedule_end:
            schedule_str = f"{config.schedule_start.strftime('%H:%M')} - {config.schedule_end.strftime('%H:%M')}"
        
        return AgentStatusResponse(
            is_enabled=config.is_enabled,
            agent_name=config.agent_name,
            is_within_schedule=is_within,
            schedule_enabled=config.schedule_enabled,
            current_schedule=schedule_str,
        )
    
    @staticmethod
    def get_prompt_for_n8n(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        request: AgentPromptRequest,
    ) -> AgentPromptResponse:
        """
        Monta prompt completo para o n8n.
        
        Chamado pelo n8n antes de enviar para a IA.
        """
        config = AgentConfigService.get_or_create(db, tenant_id)
        
        # Verificar se deve responder
        should_respond = True
        reason = None
        
        if not config.is_enabled:
            should_respond = False
            reason = "Agente desativado"
        
        is_within = config.is_within_schedule(datetime.now(timezone.utc))
        if config.schedule_enabled and not is_within:
            should_respond = False
            reason = "Fora do horário de atendimento"
        
        # Montar system prompt
        system_prompt = AgentConfigService._build_system_prompt(config, request)
        
        # Prompt de contexto específico
        context_prompt = config.get_prompt_for_context(request.context)
        
        return AgentPromptResponse(
            is_enabled=config.is_enabled,
            is_within_schedule=is_within,
            agent_name=config.agent_name,
            system_prompt=system_prompt,
            context_prompt=context_prompt,
            llm_config=LLMConfig(
                provider=config.llm_provider,
                model=config.llm_model,
                temperature=config.llm_temperature,
                max_tokens=config.llm_max_tokens,
            ),
            response_delay=config.response_delay_seconds,
            should_respond=should_respond,
            reason=reason,
        )
    
    @staticmethod
    def _build_system_prompt(config: AgentConfig, request: AgentPromptRequest) -> str:
        """Monta o system prompt completo."""
        parts = []
        
        # Identidade
        parts.append(f"Você é {config.agent_name}, {config.agent_role}.")
        
        if config.company_name:
            parts.append(f"Você trabalha na {config.company_name}.")
        
        if config.company_description:
            parts.append(f"\n{config.company_description}")
        
        # Prompt base customizado
        if config.base_prompt:
            parts.append(f"\n{config.base_prompt}")
        
        # Dados do lead (se disponível)
        if request.lead_data:
            lead_info = []
            if request.lead_data.get("name"):
                lead_info.append(f"Nome: {request.lead_data['name']}")
            if request.lead_data.get("interest"):
                lead_info.append(f"Interesse: {request.lead_data['interest']}")
            if request.lead_data.get("notes"):
                lead_info.append(f"Observações: {request.lead_data['notes']}")
            
            if lead_info:
                parts.append(f"\nInformações do cliente:\n" + "\n".join(lead_info))
        
        # Instruções gerais
        parts.append("""
Instruções:
- Seja sempre educado e profissional
- Responda de forma concisa e objetiva
- Use emojis com moderação
- Se não souber responder, ofereça transferir para um atendente
- Nunca invente informações sobre produtos ou preços
""")
        
        return "\n".join(parts)
    
    @staticmethod
    def to_response(config: AgentConfig) -> AgentConfigResponse:
        """Converte model para response schema."""
        return AgentConfigResponse(
            id=config.id,
            tenant_id=config.tenant_id,
            is_enabled=config.is_enabled,
            agent_name=config.agent_name,
            agent_role=config.agent_role,
            company_name=config.company_name,
            company_description=config.company_description,
            schedule_enabled=config.schedule_enabled,
            schedule_start=config.schedule_start.strftime("%H:%M") if config.schedule_start else None,
            schedule_end=config.schedule_end.strftime("%H:%M") if config.schedule_end else None,
            schedule_days=config.schedule_days,
            schedule_timezone=config.schedule_timezone,
            outside_hours_message=config.outside_hours_message,
            base_prompt=config.base_prompt,
            greeting_prompt=config.greeting_prompt,
            qualification_prompt=config.qualification_prompt,
            objection_prompt=config.objection_prompt,
            closing_prompt=config.closing_prompt,
            max_messages_before_human=config.max_messages_before_human,
            response_delay_seconds=config.response_delay_seconds,
            auto_qualify_score=config.auto_qualify_score,
            keywords_human=config.keywords_human,
            keywords_stop=config.keywords_stop,
            llm_provider=config.llm_provider,
            llm_model=config.llm_model,
            llm_temperature=config.llm_temperature,
            llm_max_tokens=config.llm_max_tokens,
            settings=config.settings,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
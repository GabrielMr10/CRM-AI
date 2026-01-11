"""
Schemas Pydantic para AI Agent.
"""
import uuid
from datetime import datetime, time
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class ScheduleConfig(BaseModel):
    """Configuração de horários."""
    enabled: bool = False
    start: str = "08:00"  # HH:MM
    end: str = "18:00"
    days: list[int] = Field(default=[1, 2, 3, 4, 5])  # 1=Seg, 7=Dom
    timezone: str = "America/Sao_Paulo"
    outside_message: str | None = None


class PromptsConfig(BaseModel):
    """Configuração de prompts."""
    base: str | None = None
    greeting: str | None = None
    qualification: str | None = None
    objection: str | None = None
    closing: str | None = None


class BehaviorConfig(BaseModel):
    """Configuração de comportamento."""
    max_messages_before_human: int = Field(default=10, ge=1, le=100)
    response_delay_seconds: int = Field(default=3, ge=0, le=30)
    auto_qualify_score: int = Field(default=70, ge=0, le=100)
    keywords_human: list[str] = Field(default=["atendente", "humano"])
    keywords_stop: list[str] = Field(default=["pare", "stop"])


class LLMConfig(BaseModel):
    """Configuração do modelo de linguagem."""
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=500, ge=100, le=4000)


class AgentConfigCreate(BaseModel):
    """Criação de config (geralmente automática)."""
    agent_name: str = "Laura"
    agent_role: str = "Assistente Virtual"
    company_name: str | None = None
    company_description: str | None = None


class AgentConfigUpdate(BaseModel):
    """Atualização de configuração."""
    
    # Status
    is_enabled: bool | None = None
    
    # Identidade
    agent_name: str | None = Field(None, min_length=2, max_length=100)
    agent_role: str | None = Field(None, max_length=255)
    company_name: str | None = Field(None, max_length=255)
    company_description: str | None = None
    
    # Horários
    schedule_enabled: bool | None = None
    schedule_start: str | None = None  # HH:MM
    schedule_end: str | None = None
    schedule_days: list[int] | None = None
    schedule_timezone: str | None = None
    outside_hours_message: str | None = None
    
    # Prompts
    base_prompt: str | None = None
    greeting_prompt: str | None = None
    qualification_prompt: str | None = None
    objection_prompt: str | None = None
    closing_prompt: str | None = None
    
    # Comportamento
    max_messages_before_human: int | None = Field(None, ge=1, le=100)
    response_delay_seconds: int | None = Field(None, ge=0, le=30)
    auto_qualify_score: int | None = Field(None, ge=0, le=100)
    keywords_human: list[str] | None = None
    keywords_stop: list[str] | None = None
    
    # LLM
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_temperature: float | None = Field(None, ge=0, le=2)
    llm_max_tokens: int | None = Field(None, ge=100, le=4000)
    
    # Extras
    settings: dict[str, Any] | None = None


class AgentConfigResponse(BaseModel):
    """Resposta com config completa."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    tenant_id: uuid.UUID
    
    # Status
    is_enabled: bool
    
    # Identidade
    agent_name: str
    agent_role: str
    company_name: str | None
    company_description: str | None
    
    # Horários
    schedule_enabled: bool
    schedule_start: str | None  # Convertido para string HH:MM
    schedule_end: str | None
    schedule_days: list[int]
    schedule_timezone: str
    outside_hours_message: str | None
    
    # Prompts
    base_prompt: str | None
    greeting_prompt: str | None
    qualification_prompt: str | None
    objection_prompt: str | None
    closing_prompt: str | None
    
    # Comportamento
    max_messages_before_human: int
    response_delay_seconds: int
    auto_qualify_score: int
    keywords_human: list[str]
    keywords_stop: list[str]
    
    # LLM
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    
    # Extras
    settings: dict[str, Any]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime


class AgentStatusResponse(BaseModel):
    """Status resumido do agente."""
    
    is_enabled: bool
    agent_name: str
    is_within_schedule: bool
    schedule_enabled: bool
    current_schedule: str | None  # "08:00 - 18:00"


class AgentPromptRequest(BaseModel):
    """Requisição do n8n para obter prompt."""
    
    phone: str
    context: str = "base"  # base, greeting, qualification, objection, closing
    lead_data: dict | None = None
    conversation_history: list[dict] | None = None


class AgentPromptResponse(BaseModel):
    """Resposta com prompt montado para o n8n."""
    
    is_enabled: bool
    is_within_schedule: bool
    agent_name: str
    system_prompt: str
    context_prompt: str | None
    llm_config: LLMConfig
    response_delay: int
    should_respond: bool
    reason: str | None = None  # Se não deve responder, por quê
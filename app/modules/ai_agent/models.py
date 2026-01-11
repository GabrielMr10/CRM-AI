"""
Model de configuração do AI Agent (Laura).
"""
import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Time
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    from app.modules.tenants.models import Tenant


class AgentConfig(Base):
    """
    Configuração do agente IA (Laura) por tenant.
    
    Cada tenant tem UMA configuração.
    """
    
    __tablename__ = "agent_configs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    # ==================== STATUS ====================
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Agente ativo globalmente",
    )
    
    # ==================== IDENTIDADE ====================
    agent_name: Mapped[str] = mapped_column(
        String(100),
        default="Laura",
        nullable=False,
        comment="Nome do agente",
    )
    
    agent_role: Mapped[str] = mapped_column(
        String(255),
        default="Assistente Virtual",
        nullable=False,
        comment="Papel/função do agente",
    )
    
    company_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Nome da empresa (para o prompt)",
    )
    
    company_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Descrição da empresa/serviços",
    )
    
    # ==================== HORÁRIOS ====================
    schedule_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Respeitar horário de funcionamento",
    )
    
    schedule_start: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        default=time(8, 0),
        comment="Hora início atendimento",
    )
    
    schedule_end: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        default=time(18, 0),
        comment="Hora fim atendimento",
    )
    
    schedule_days: Mapped[list] = mapped_column(
        JSONB,
        default=lambda: [1, 2, 3, 4, 5],  # Seg a Sex
        nullable=False,
        comment="Dias da semana (1=Seg, 7=Dom)",
    )
    
    schedule_timezone: Mapped[str] = mapped_column(
        String(50),
        default="America/Sao_Paulo",
        nullable=False,
        comment="Timezone",
    )
    
    outside_hours_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Mensagem fora do horário",
    )
    
    # ==================== PROMPTS ====================
    base_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Prompt base do agente",
    )
    
    greeting_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Prompt para primeira mensagem",
    )
    
    qualification_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Prompt para qualificação de leads",
    )
    
    objection_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Prompt para tratamento de objeções",
    )
    
    closing_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Prompt para fechamento",
    )
    
    # ==================== COMPORTAMENTO ====================
    max_messages_before_human: Mapped[int] = mapped_column(
        default=10,
        nullable=False,
        comment="Máximo de mensagens antes de chamar humano",
    )
    
    response_delay_seconds: Mapped[int] = mapped_column(
        default=3,
        nullable=False,
        comment="Delay antes de responder (simula digitação)",
    )
    
    auto_qualify_score: Mapped[int] = mapped_column(
        default=70,
        nullable=False,
        comment="Score mínimo para qualificar automaticamente",
    )
    
    # ==================== CONFIGURAÇÕES EXTRAS ====================
    settings: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Configurações extras",
    )
    
    # Palavras-chave para ações
    keywords_human: Mapped[list] = mapped_column(
        JSONB,
        default=lambda: ["atendente", "humano", "pessoa", "falar com alguém"],
        nullable=False,
        comment="Keywords para transferir para humano",
    )
    
    keywords_stop: Mapped[list] = mapped_column(
        JSONB,
        default=lambda: ["pare", "stop", "parar", "chega"],
        nullable=False,
        comment="Keywords para pausar bot",
    )
    
    # ==================== INTEGRAÇÕES ====================
    llm_provider: Mapped[str] = mapped_column(
        String(50),
        default="anthropic",
        nullable=False,
        comment="Provider: anthropic, openai",
    )
    
    llm_model: Mapped[str] = mapped_column(
        String(100),
        default="claude-sonnet-4-20250514",
        nullable=False,
        comment="Modelo a usar",
    )
    
    llm_temperature: Mapped[float] = mapped_column(
        default=0.7,
        nullable=False,
        comment="Temperatura do modelo",
    )
    
    llm_max_tokens: Mapped[int] = mapped_column(
        default=500,
        nullable=False,
        comment="Máximo de tokens na resposta",
    )
    
    # ==================== RELACIONAMENTOS ====================
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    
    def __repr__(self) -> str:
        return f"<AgentConfig {self.agent_name} (tenant={self.tenant_id})>"
    
    def is_within_schedule(self, current_time: datetime) -> bool:
        """Verifica se está dentro do horário de atendimento."""
        if not self.schedule_enabled:
            return True
        
        # Converter para timezone do tenant
        import pytz
        tz = pytz.timezone(self.schedule_timezone)
        local_time = current_time.astimezone(tz)
        
        # Verificar dia da semana (1=Segunda, 7=Domingo)
        weekday = local_time.isoweekday()
        if weekday not in self.schedule_days:
            return False
        
        # Verificar horário
        current = local_time.time()
        if self.schedule_start and self.schedule_end:
            return self.schedule_start <= current <= self.schedule_end
        
        return True
    
    def get_prompt_for_context(self, context: str = "base") -> str:
        """Retorna prompt apropriado para o contexto."""
        prompts = {
            "base": self.base_prompt,
            "greeting": self.greeting_prompt,
            "qualification": self.qualification_prompt,
            "objection": self.objection_prompt,
            "closing": self.closing_prompt,
        }
        return prompts.get(context) or self.base_prompt or ""
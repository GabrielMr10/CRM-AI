"""
Models do Pipeline: Pipeline, Stage e Deal.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    from app.modules.tenants.models import Tenant
    from app.modules.users.models import User
    from app.modules.leads.models import Lead


class Pipeline(Base):
    """
    Pipeline = Funil de vendas.
    
    Cada tenant pode ter múltiplos pipelines.
    Ex: "Vendas Solar", "Vendas Residencial", "Pós-venda"
    """
    
    __tablename__ = "pipelines"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome do pipeline",
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Pipeline padrão do tenant",
    )
    
    # Configurações
    settings: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    
    # Relacionamentos
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
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
    stages: Mapped[list["Stage"]] = relationship(
        "Stage",
        back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="Stage.position",
    )
    
    def __repr__(self) -> str:
        return f"<Pipeline {self.name}>"


class Stage(Base):
    """
    Stage = Coluna do Kanban.
    
    Cada stage tem uma posição (ordem) no pipeline.
    Ex: "Novo" (1), "Em contato" (2), "Proposta" (3), "Fechado" (4)
    """
    
    __tablename__ = "stages"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Ordem no pipeline (0, 1, 2...)",
    )
    
    color: Mapped[str] = mapped_column(
        String(20),
        default="#6B7280",
        nullable=False,
        comment="Cor da coluna (hex)",
    )
    
    is_won: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Stage de vitória (fechou negócio)",
    )
    
    is_lost: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Stage de perda",
    )
    
    # Automações
    auto_probability: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Probabilidade automática (0-100%)",
    )
    
    # Relacionamentos
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="stages")
    deals: Mapped[list["Deal"]] = relationship(
        "Deal",
        back_populates="stage",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Stage {self.name} (pos={self.position})>"


class Deal(Base):
    """
    Deal = Card/Negociação no Kanban.
    
    Representa uma oportunidade de venda vinculada a um Lead.
    """
    
    __tablename__ = "deals"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Título do deal",
    )
    
    value: Mapped[float] = mapped_column(
        Float,
        default=0,
        nullable=False,
        comment="Valor do negócio (R$)",
    )
    
    probability: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Probabilidade de fechamento (0-100%)",
    )
    
    expected_close_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data esperada de fechamento",
    )
    
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Posição dentro do stage",
    )
    
    # Status
    is_won: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lost_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Dados extras
    custom_fields: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    
    # Relacionamentos
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
    
    won_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lost_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    pipeline: Mapped["Pipeline"] = relationship("Pipeline")
    stage: Mapped["Stage"] = relationship("Stage", back_populates="deals")
    lead: Mapped["Lead | None"] = relationship("Lead")
    assigned_to: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_to_id])
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    
    def __repr__(self) -> str:
        return f"<Deal {self.title} (R${self.value})>"
    
    @property
    def weighted_value(self) -> float:
        """Valor ponderado pela probabilidade."""
        return self.value * (self.probability / 100)
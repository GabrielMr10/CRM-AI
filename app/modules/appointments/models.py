"""
Model SQLAlchemy do Appointment.

TABELA: appointments
Representa agendamentos de visitas/reuniões.

USO:
    from app.modules.appointments.models import Appointment, AppointmentStatus, AppointmentSource

    appointment = Appointment(
        title="Visita Solar - João",
        start_datetime=datetime(2026, 1, 20, 14, 0),
        end_datetime=datetime(2026, 1, 20, 15, 0),
        tenant_id=tenant.id,
        employee_id=user.id,
    )
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    from app.modules.tenants.models import Tenant
    from app.modules.users.models import User
    from app.modules.leads.models import Lead


class AppointmentStatus(str, Enum):
    """Status do agendamento."""
    PENDING = "pending"          # Aguardando confirmação
    CONFIRMED = "confirmed"      # Confirmado
    CANCELLED = "cancelled"      # Cancelado
    COMPLETED = "completed"      # Concluído
    NO_SHOW = "no_show"          # Cliente não compareceu


class AppointmentSource(str, Enum):
    """Origem do agendamento."""
    AI = "ai"                    # Agendado pela IA (Laura)
    HUMAN_APP = "human_app"      # Agendado pelo funcionário no CRM
    HUMAN_ADMIN = "human_admin"  # Agendado pelo admin/recepcionista
    WHATSAPP = "whatsapp"        # Cliente pediu via WhatsApp (manual)


class Appointment(Base):
    """
    Agendamento de visita/reunião.

    Cada agendamento pertence a um tenant, é atribuído a um funcionário
    e pode estar vinculado a um lead.

    Attributes:
        id: UUID único
        title: Título do agendamento
        description: Descrição detalhada
        start_datetime: Data/hora de início
        end_datetime: Data/hora de término
        status: Status atual (pending, confirmed, etc.)
        source: Origem (ai, human_app, etc.)
        employee_id: Funcionário responsável
        lead_id: Lead vinculado (opcional)
        client_name: Nome do cliente (se não tiver lead)
        client_phone: Telefone do cliente
        notes: Observações
        location: Local/endereço
    """

    __tablename__ = "appointments"

    __table_args__ = (
        Index("ix_appointments_tenant_employee", "tenant_id", "employee_id"),
        Index("ix_appointments_tenant_date", "tenant_id", "start_datetime"),
        Index("ix_appointments_employee_date", "employee_id", "start_datetime"),
    )

    # ==================== IDENTIFICAÇÃO ====================
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # ==================== DADOS DO AGENDAMENTO ====================
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Título do agendamento",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Descrição detalhada",
    )

    # ==================== DATA E HORA ====================
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Data/hora de início",
    )

    end_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data/hora de término",
    )

    # ==================== STATUS E ORIGEM ====================
    status: Mapped[str] = mapped_column(
        String(50),
        default=AppointmentStatus.PENDING.value,
        nullable=False,
        index=True,
        comment="Status: pending, confirmed, cancelled, completed, no_show",
    )

    source: Mapped[str] = mapped_column(
        String(50),
        default=AppointmentSource.HUMAN_APP.value,
        nullable=False,
        comment="Origem: ai, human_app, human_admin, whatsapp",
    )

    # ==================== RELACIONAMENTOS ====================
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Funcionário responsável",
    )

    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Lead vinculado (opcional)",
    )

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Usuário que criou o agendamento",
    )

    # ==================== DADOS DO CLIENTE ====================
    client_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Nome do cliente (se não tiver lead)",
    )

    client_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Telefone do cliente",
    )

    # ==================== NOTAS E LOCALIZAÇÃO ====================
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Observações",
    )

    location: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Local/endereço da visita",
    )

    # ==================== TIMESTAMPS ====================
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

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de cancelamento",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de conclusão",
    )

    # ==================== RELATIONSHIPS ====================
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="appointments",
    )

    employee: Mapped["User"] = relationship(
        "User",
        foreign_keys=[employee_id],
        back_populates="appointments",
    )

    lead: Mapped["Lead | None"] = relationship(
        "Lead",
        back_populates="appointments",
    )

    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )

    # ==================== MÉTODOS ====================
    def __repr__(self) -> str:
        return f"<Appointment {self.title} - {self.start_datetime}>"

    @property
    def appointment_status(self) -> AppointmentStatus:
        """Retorna status como Enum."""
        return AppointmentStatus(self.status)

    @property
    def appointment_source(self) -> AppointmentSource:
        """Retorna source como Enum."""
        return AppointmentSource(self.source)

    @property
    def is_cancelled(self) -> bool:
        """Verifica se foi cancelado."""
        return self.status == AppointmentStatus.CANCELLED.value

    @property
    def is_completed(self) -> bool:
        """Verifica se foi concluído."""
        return self.status == AppointmentStatus.COMPLETED.value

    @property
    def is_pending(self) -> bool:
        """Verifica se está pendente."""
        return self.status == AppointmentStatus.PENDING.value

    @property
    def is_from_ai(self) -> bool:
        """Verifica se foi criado pela IA."""
        return self.source == AppointmentSource.AI.value

    @property
    def duration_minutes(self) -> int:
        """Retorna duração em minutos."""
        delta = self.end_datetime - self.start_datetime
        return int(delta.total_seconds() / 60)
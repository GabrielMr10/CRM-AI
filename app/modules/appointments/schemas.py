"""
Schemas Pydantic para validação de request/response de Appointments.

USO:
    from app.modules.appointments.schemas import AppointmentCreate, AppointmentResponse

    @router.post("/", response_model=AppointmentResponse)
    def create(data: AppointmentCreate):
        ...
"""
from __future__ import annotations

import uuid
from datetime import datetime, date, time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ==================== ENUMS ====================

class AppointmentStatus(str, Enum):
    """Status do agendamento."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class AppointmentSource(str, Enum):
    """Origem do agendamento."""
    AI = "ai"
    HUMAN_APP = "human_app"
    HUMAN_ADMIN = "human_admin"
    WHATSAPP = "whatsapp"


# ==================== CREATE ====================

class AppointmentCreate(BaseModel):
    """Schema para criação de agendamento (via CRM)."""

    title: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Título do agendamento",
        examples=["Visita Solar - João"],
    )

    description: str | None = Field(
        None,
        max_length=2000,
        description="Descrição detalhada",
    )

    start_datetime: datetime = Field(
        ...,
        description="Data/hora de início",
    )

    end_datetime: datetime = Field(
        ...,
        description="Data/hora de término",
    )

    employee_id: uuid.UUID = Field(
        ...,
        description="ID do funcionário responsável",
    )

    lead_id: uuid.UUID | None = Field(
        None,
        description="ID do lead vinculado (opcional)",
    )

    client_name: str | None = Field(
        None,
        max_length=255,
        description="Nome do cliente (se não tiver lead)",
    )

    client_phone: str | None = Field(
        None,
        max_length=20,
        description="Telefone do cliente",
    )

    notes: str | None = Field(
        None,
        max_length=2000,
        description="Observações",
    )

    location: str | None = Field(
        None,
        max_length=500,
        description="Local/endereço",
    )

    source: AppointmentSource = Field(
        AppointmentSource.HUMAN_APP,
        description="Origem do agendamento",
    )

    @field_validator("end_datetime")
    @classmethod
    def validate_end_after_start(cls, v, info):
        """Valida que end_datetime é após start_datetime."""
        if "start_datetime" in info.data and v <= info.data["start_datetime"]:
            raise ValueError("Data/hora de término deve ser após o início")
        return v


# ==================== CREATE BY AI ====================

class AppointmentCreateByAI(BaseModel):
    """Schema simplificado para a IA agendar via n8n."""

    title: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Título do agendamento",
    )

    start_datetime: datetime = Field(
        ...,
        description="Data/hora de início",
    )

    end_datetime: datetime = Field(
        ...,
        description="Data/hora de término",
    )

    employee_id: uuid.UUID = Field(
        ...,
        description="ID do funcionário",
    )

    lead_id: uuid.UUID | None = Field(
        None,
        description="ID do lead (opcional)",
    )

    client_name: str = Field(
        ...,
        max_length=255,
        description="Nome do cliente",
    )

    client_phone: str = Field(
        ...,
        max_length=20,
        description="Telefone do cliente",
    )

    notes: str | None = Field(
        None,
        max_length=2000,
        description="Observações",
    )

    location: str | None = Field(
        None,
        max_length=500,
        description="Local/endereço",
    )

    @field_validator("end_datetime")
    @classmethod
    def validate_end_after_start(cls, v, info):
        """Valida que end_datetime é após start_datetime."""
        if "start_datetime" in info.data and v <= info.data["start_datetime"]:
            raise ValueError("Data/hora de término deve ser após o início")
        return v


# ==================== UPDATE ====================

class AppointmentUpdate(BaseModel):
    """Schema para atualização parcial de agendamento."""

    title: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    employee_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    client_name: str | None = Field(None, max_length=255)
    client_phone: str | None = Field(None, max_length=20)
    notes: str | None = Field(None, max_length=2000)
    location: str | None = Field(None, max_length=500)
    status: AppointmentStatus | None = None


# ==================== RESPONSE ====================

class AppointmentResponse(BaseModel):
    """Schema de resposta de agendamento."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    start_datetime: datetime
    end_datetime: datetime
    status: AppointmentStatus
    source: AppointmentSource
    tenant_id: uuid.UUID
    employee_id: uuid.UUID
    lead_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    client_name: str | None
    client_phone: str | None
    notes: str | None
    location: str | None
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None
    completed_at: datetime | None

    # Campos extras para o frontend
    employee_name: str | None = None
    lead_name: str | None = None


class AppointmentListResponse(BaseModel):
    """Schema para listagem com paginação."""

    items: list[AppointmentResponse]
    total: int
    page: int
    pages: int
    per_page: int


# ==================== FULLCALENDAR FORMAT ====================

class CalendarEvent(BaseModel):
    """Formato que o FullCalendar espera."""

    id: str
    title: str
    start: str  # ISO format
    end: str    # ISO format
    backgroundColor: str
    borderColor: str
    textColor: str = "#ffffff"
    extendedProps: dict[str, Any]


# ==================== SLOTS DISPONÍVEIS ====================

class AvailableSlotsRequest(BaseModel):
    """Request para buscar horários disponíveis."""

    target_date: date = Field(..., description="Data para verificar (YYYY-MM-DD)")
    employee_id: uuid.UUID = Field(..., description="ID do funcionário")
    duration_minutes: int = Field(60, ge=15, le=480, description="Duração em minutos")


class AvailableSlot(BaseModel):
    """Um slot de horário disponível."""

    start: time
    end: time
    start_datetime: datetime
    end_datetime: datetime


class AvailableSlotsResponse(BaseModel):
    """Resposta com horários disponíveis."""

    target_date: date
    employee_id: uuid.UUID
    employee_name: str
    slots: list[AvailableSlot]
    business_hours: dict[str, str]  # Ex: {"start": "08:00", "end": "18:00"}


# ==================== STATS ====================

class AppointmentStats(BaseModel):
    """Estatísticas de agendamentos."""

    total: int
    by_status: dict[str, int]
    by_source: dict[str, int]
    today: int
    this_week: int
    this_month: int
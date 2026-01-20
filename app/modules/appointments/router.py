"""
Router - Endpoints da API de Appointments.

Prefixo: /api/v1/appointments
Tags: ["Appointments"]

USO:
    from app.modules.appointments.router import router as appointments_router
    app.include_router(appointments_router, prefix="/api/v1/appointments", tags=["Appointments"])
"""
import uuid
from datetime import datetime, date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.modules.appointments.schemas import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentCreateByAI,
    AppointmentResponse,
    CalendarEvent,
    AvailableSlotsResponse,
    AppointmentStats,
    AppointmentStatus,
)
from app.modules.appointments.service import AppointmentService


router = APIRouter()


# ==================== MINHA AGENDA ====================

@router.get(
    "/my-agenda",
    response_model=list[CalendarEvent],
    summary="Minha agenda (FullCalendar)",
    description="Retorna agendamentos do usuário logado no formato do FullCalendar.",
)
def get_my_agenda(
    start: datetime = Query(..., description="Data/hora início (ISO format)"),
    end: datetime = Query(..., description="Data/hora fim (ISO format)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retorna agendamentos do funcionário logado.

    Formato compatível com FullCalendar:
    - id, title, start, end (ISO format)
    - backgroundColor, borderColor, textColor
    - extendedProps com dados extras
    """
    return AppointmentService.get_my_agenda(
        db,
        tenant_id=current_user.tenant_id,
        employee_id=current_user.id,
        start_date=start,
        end_date=end,
    )


# ==================== AGENDA DE FUNCIONÁRIO ====================

@router.get(
    "/employee/{employee_id}",
    response_model=list[CalendarEvent],
    summary="Agenda de funcionário",
    description="Retorna agendamentos de um funcionário específico (para admin).",
)
def get_employee_agenda(
    employee_id: uuid.UUID,
    start: datetime = Query(..., description="Data/hora início"),
    end: datetime = Query(..., description="Data/hora fim"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retorna agenda de um funcionário específico."""
    return AppointmentService.get_my_agenda(
        db,
        tenant_id=current_user.tenant_id,
        employee_id=employee_id,
        start_date=start,
        end_date=end,
    )


# ==================== SLOTS DISPONÍVEIS (PARA IA) ====================

@router.get(
    "/slots-available",
    response_model=AvailableSlotsResponse,
    summary="Horários disponíveis",
    description="Retorna horários livres para a IA oferecer ao cliente.",
)
def get_available_slots(
    target_date: date = Query(..., alias="date", description="Data (YYYY-MM-DD)"),
    employee_id: uuid.UUID = Query(..., description="ID do funcionário"),
    duration: int = Query(60, ge=15, le=480, description="Duração em minutos"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retorna horários disponíveis para agendamento.

    Usado pela IA para oferecer opções ao cliente.
    Considera:
    - Horário comercial (08:00 - 18:00)
    - Horário de almoço (12:00 - 13:00)
    - Agendamentos já existentes
    """
    return AppointmentService.get_available_slots(
        db,
        tenant_id=current_user.tenant_id,
        employee_id=employee_id,
        target_date=target_date,
        duration_minutes=duration,
    )


# ==================== ESTATÍSTICAS ====================

@router.get(
    "/stats/summary",
    response_model=AppointmentStats,
    summary="Estatísticas",
    description="Retorna estatísticas de agendamentos.",
)
def get_stats(
    employee_id: uuid.UUID | None = Query(None, description="Filtrar por funcionário"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retorna estatísticas de agendamentos do tenant."""
    return AppointmentService.get_stats(
        db,
        tenant_id=current_user.tenant_id,
        employee_id=employee_id,
    )


# ==================== LISTAR ====================

@router.get(
    "/",
    response_model=list[AppointmentResponse],
    summary="Listar agendamentos",
    description="Lista agendamentos com filtros opcionais.",
)
def list_appointments(
    employee_id: uuid.UUID | None = Query(None, description="Filtrar por funcionário"),
    start_date: datetime | None = Query(None, description="Data início"),
    end_date: datetime | None = Query(None, description="Data fim"),
    status: AppointmentStatus | None = Query(None, description="Filtrar por status"),
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(100, ge=1, le=500, description="Limite"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Lista agendamentos com filtros."""
    return AppointmentService.get_all(
        db,
        tenant_id=current_user.tenant_id,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        skip=skip,
        limit=limit,
    )


# ==================== CRIAR ====================

@router.post(
    "/",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar agendamento",
    description="Cria um novo agendamento (via CRM).",
)
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Cria novo agendamento.

    Valida:
    - Datas (end > start)
    - Conflito de horário com o funcionário
    """
    return AppointmentService.create(
        db,
        tenant_id=current_user.tenant_id,
        data=data,
        created_by_id=current_user.id,
    )


# ==================== CRIAR (IA) ====================

@router.post(
    "/ai-schedule",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agendar via IA",
    description="Cria agendamento via IA (n8n). Sempre com source=AI e status=CONFIRMED.",
)
def create_appointment_by_ai(
    data: AppointmentCreateByAI,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Cria agendamento via IA.

    Usado pelo n8n quando a Laura agenda uma visita.
    Sempre cria com:
    - source = "ai"
    - status = "confirmed"
    """
    return AppointmentService.create_by_ai(
        db,
        tenant_id=current_user.tenant_id,
        data=data,
    )


# ==================== DETALHE ====================

@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Detalhe do agendamento",
    description="Retorna detalhes de um agendamento específico.",
)
def get_appointment(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retorna detalhes de um agendamento."""
    return AppointmentService.get_by_id(
        db,
        appointment_id=appointment_id,
        tenant_id=current_user.tenant_id,
    )


# ==================== ATUALIZAR ====================

@router.patch(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Atualizar agendamento",
    description="Atualiza um agendamento existente.",
)
def update_appointment(
    appointment_id: uuid.UUID,
    data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Atualiza agendamento.

    Não permite modificar agendamentos cancelados ou concluídos.
    Valida conflito se mudar horário ou funcionário.
    """
    return AppointmentService.update(
        db,
        appointment_id=appointment_id,
        tenant_id=current_user.tenant_id,
        data=data,
    )


# ==================== CONFIRMAR ====================

@router.post(
    "/{appointment_id}/confirm",
    response_model=AppointmentResponse,
    summary="Confirmar agendamento",
    description="Confirma um agendamento pendente.",
)
def confirm_appointment(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Confirma um agendamento pendente."""
    return AppointmentService.confirm(
        db,
        appointment_id=appointment_id,
        tenant_id=current_user.tenant_id,
    )


# ==================== CANCELAR ====================

@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentResponse,
    summary="Cancelar agendamento",
    description="Cancela um agendamento.",
)
def cancel_appointment(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Cancela um agendamento."""
    return AppointmentService.cancel(
        db,
        appointment_id=appointment_id,
        tenant_id=current_user.tenant_id,
    )


# ==================== CONCLUIR ====================

@router.post(
    "/{appointment_id}/complete",
    response_model=AppointmentResponse,
    summary="Marcar como concluído",
    description="Marca agendamento como concluído.",
)
def complete_appointment(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Marca agendamento como concluído."""
    return AppointmentService.complete(
        db,
        appointment_id=appointment_id,
        tenant_id=current_user.tenant_id,
    )


# ==================== NO-SHOW ====================

@router.post(
    "/{appointment_id}/no-show",
    response_model=AppointmentResponse,
    summary="Marcar como no-show",
    description="Marca que o cliente não compareceu.",
)
def mark_no_show(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Marca que o cliente não compareceu."""
    return AppointmentService.mark_no_show(
        db,
        appointment_id=appointment_id,
        tenant_id=current_user.tenant_id,
    )


# ==================== DELETAR ====================

@router.delete(
    "/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar agendamento",
    description="Remove um agendamento permanentemente.",
)
def delete_appointment(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Remove agendamento permanentemente."""
    AppointmentService.delete(
        db,
        appointment_id=appointment_id,
        tenant_id=current_user.tenant_id,
    )
    return None
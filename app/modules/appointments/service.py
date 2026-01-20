"""
Service - Lógica de negócio de Appointments.

USO:
    from app.modules.appointments.service import AppointmentService

    service = AppointmentService()
    appointments = service.get_my_agenda(db, tenant_id, employee_id, start, end)
"""
import uuid
from datetime import datetime, date, time, timedelta

from sqlalchemy.orm import Session

from app.modules.appointments.models import Appointment, AppointmentStatus, AppointmentSource
from app.modules.appointments.repository import AppointmentRepository
from app.modules.appointments.schemas import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentCreateByAI,
    AppointmentResponse,
    CalendarEvent,
    AvailableSlot,
    AvailableSlotsResponse,
    AppointmentStats,
)
from app.modules.appointments.exceptions import (
    AppointmentNotFoundException,
    AppointmentConflictException,
    InvalidDateRangeException,
    AppointmentCannotBeModifiedException,
)


class AppointmentService:
    """
    Serviço de Agendamentos.
    Contém lógica de negócio e validações.
    """

    # Configurações de horário comercial (pode vir do tenant.settings depois)
    BUSINESS_START = time(8, 0)   # 08:00
    BUSINESS_END = time(18, 0)    # 18:00
    SLOT_DURATION = 60            # minutos padrão
    LUNCH_START = time(12, 0)     # 12:00
    LUNCH_END = time(13, 0)       # 13:00

    # ==================== READ ====================

    @staticmethod
    def get_by_id(
        db: Session,
        appointment_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> AppointmentResponse:
        """Busca agendamento por ID."""
        appointment = AppointmentRepository.get_by_id(db, appointment_id, tenant_id)

        if not appointment:
            raise AppointmentNotFoundException()

        return AppointmentService._to_response(appointment)

    @staticmethod
    def get_all(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        employee_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        status: AppointmentStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AppointmentResponse]:
        """Lista agendamentos com filtros."""
        appointments = AppointmentRepository.get_all(
            db,
            tenant_id,
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
            skip=skip,
            limit=limit,
        )

        return [AppointmentService._to_response(a) for a in appointments]

    @staticmethod
    def get_my_agenda(
        db: Session,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Retorna agendamentos no formato do FullCalendar."""
        appointments = AppointmentRepository.get_by_employee(
            db, tenant_id, employee_id, start_date, end_date
        )

        return [AppointmentService._to_calendar_event(a) for a in appointments]

    @staticmethod
    def get_available_slots(
        db: Session,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        target_date: date,
        duration_minutes: int = 60,
    ) -> AvailableSlotsResponse:
        """
        Retorna horários disponíveis para a IA oferecer ao cliente.

        Algoritmo:
        1. Busca todos os agendamentos do dia
        2. Gera slots a cada X minutos dentro do horário comercial
        3. Remove slots que conflitam com agendamentos existentes
        4. Remove horário de almoço
        """
        # Busca horários já ocupados
        booked = AppointmentRepository.get_booked_slots(db, tenant_id, employee_id, target_date)
        booked_ranges = [(a.start_datetime, a.end_datetime) for a in booked]

        # Gera todos os slots possíveis
        available_slots = []
        current_time = datetime.combine(target_date, AppointmentService.BUSINESS_START)
        end_of_day = datetime.combine(target_date, AppointmentService.BUSINESS_END)

        while current_time + timedelta(minutes=duration_minutes) <= end_of_day:
            slot_start = current_time
            slot_end = current_time + timedelta(minutes=duration_minutes)

            # Pula horário de almoço
            lunch_start = datetime.combine(target_date, AppointmentService.LUNCH_START)
            lunch_end = datetime.combine(target_date, AppointmentService.LUNCH_END)

            if slot_start < lunch_end and slot_end > lunch_start:
                # Slot conflita com almoço, pula para depois do almoço
                current_time = lunch_end
                continue

            # Verifica se o slot está livre
            is_available = True
            for booked_start, booked_end in booked_ranges:
                # Verifica sobreposição
                if not (slot_end <= booked_start or slot_start >= booked_end):
                    is_available = False
                    break

            if is_available:
                available_slots.append(AvailableSlot(
                    start=slot_start.time(),
                    end=slot_end.time(),
                    start_datetime=slot_start,
                    end_datetime=slot_end,
                ))

            current_time += timedelta(minutes=duration_minutes)

        # Busca nome do funcionário
        from app.modules.users.repository import UserRepository
        employee = UserRepository.get_by_id(db, employee_id)
        employee_name = employee.full_name if employee else "Funcionário"

        return AvailableSlotsResponse(
            target_date=target_date,
            employee_id=employee_id,
            employee_name=employee_name,
            slots=available_slots,
            business_hours={
                "start": AppointmentService.BUSINESS_START.strftime("%H:%M"),
                "end": AppointmentService.BUSINESS_END.strftime("%H:%M"),
            },
        )

    # ==================== CREATE ====================

    @staticmethod
    def create(
        db: Session,
        tenant_id: uuid.UUID,
        data: AppointmentCreate,
        created_by_id: uuid.UUID | None = None,
    ) -> AppointmentResponse:
        """Cria novo agendamento (via CRM)."""
        # Valida datas
        if data.end_datetime <= data.start_datetime:
            raise InvalidDateRangeException()

        # Verifica conflito de horário
        if AppointmentRepository.check_conflict(
            db,
            tenant_id,
            data.employee_id,
            data.start_datetime,
            data.end_datetime,
        ):
            raise AppointmentConflictException()

        appointment = AppointmentRepository.create(db, tenant_id, data, created_by_id)

        return AppointmentService._to_response(appointment)

    @staticmethod
    def create_by_ai(
        db: Session,
        tenant_id: uuid.UUID,
        data: AppointmentCreateByAI,
    ) -> AppointmentResponse:
        """Cria agendamento via IA (n8n)."""
        # Valida datas
        if data.end_datetime <= data.start_datetime:
            raise InvalidDateRangeException()

        # Verifica conflito mesmo assim (segurança)
        if AppointmentRepository.check_conflict(
            db,
            tenant_id,
            data.employee_id,
            data.start_datetime,
            data.end_datetime,
        ):
            raise AppointmentConflictException()

        appointment = AppointmentRepository.create_by_ai(db, tenant_id, data)

        return AppointmentService._to_response(appointment)

    # ==================== UPDATE ====================

    @staticmethod
    def update(
        db: Session,
        appointment_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: AppointmentUpdate,
    ) -> AppointmentResponse:
        """Atualiza um agendamento."""
        appointment = AppointmentRepository.get_by_id(db, appointment_id, tenant_id)

        if not appointment:
            raise AppointmentNotFoundException()

        # Não permite modificar agendamentos cancelados ou concluídos
        if appointment.status in [
            AppointmentStatus.CANCELLED.value,
            AppointmentStatus.COMPLETED.value,
        ]:
            raise AppointmentCannotBeModifiedException()

        # Se mudou horário, verifica conflito
        if data.start_datetime or data.end_datetime or data.employee_id:
            start = data.start_datetime or appointment.start_datetime
            end = data.end_datetime or appointment.end_datetime
            employee = data.employee_id or appointment.employee_id

            if end <= start:
                raise InvalidDateRangeException()

            if AppointmentRepository.check_conflict(
                db,
                tenant_id,
                employee,
                start,
                end,
                exclude_id=appointment_id,
            ):
                raise AppointmentConflictException()

        appointment = AppointmentRepository.update(db, appointment, data)

        return AppointmentService._to_response(appointment)

    # ==================== STATUS CHANGES ====================

    @staticmethod
    def cancel(
        db: Session,
        appointment_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> AppointmentResponse:
        """Cancela um agendamento."""
        appointment = AppointmentRepository.get_by_id(db, appointment_id, tenant_id)

        if not appointment:
            raise AppointmentNotFoundException()

        if appointment.status == AppointmentStatus.CANCELLED.value:
            raise AppointmentCannotBeModifiedException("Agendamento já está cancelado")

        appointment = AppointmentRepository.cancel(db, appointment)

        return AppointmentService._to_response(appointment)

    @staticmethod
    def confirm(
        db: Session,
        appointment_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> AppointmentResponse:
        """Confirma um agendamento pendente."""
        appointment = AppointmentRepository.get_by_id(db, appointment_id, tenant_id)

        if not appointment:
            raise AppointmentNotFoundException()

        if appointment.status != AppointmentStatus.PENDING.value:
            raise AppointmentCannotBeModifiedException(
                "Apenas agendamentos pendentes podem ser confirmados"
            )

        appointment = AppointmentRepository.confirm(db, appointment)

        return AppointmentService._to_response(appointment)

    @staticmethod
    def complete(
        db: Session,
        appointment_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> AppointmentResponse:
        """Marca agendamento como concluído."""
        appointment = AppointmentRepository.get_by_id(db, appointment_id, tenant_id)

        if not appointment:
            raise AppointmentNotFoundException()

        if appointment.status in [
            AppointmentStatus.CANCELLED.value,
            AppointmentStatus.COMPLETED.value,
        ]:
            raise AppointmentCannotBeModifiedException()

        appointment = AppointmentRepository.complete(db, appointment)

        return AppointmentService._to_response(appointment)

    @staticmethod
    def mark_no_show(
        db: Session,
        appointment_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> AppointmentResponse:
        """Marca agendamento como no-show."""
        appointment = AppointmentRepository.get_by_id(db, appointment_id, tenant_id)

        if not appointment:
            raise AppointmentNotFoundException()

        if appointment.status in [
            AppointmentStatus.CANCELLED.value,
            AppointmentStatus.COMPLETED.value,
        ]:
            raise AppointmentCannotBeModifiedException()

        appointment = AppointmentRepository.mark_no_show(db, appointment)

        return AppointmentService._to_response(appointment)

    # ==================== DELETE ====================

    @staticmethod
    def delete(
        db: Session,
        appointment_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        """Remove agendamento do banco."""
        appointment = AppointmentRepository.get_by_id(db, appointment_id, tenant_id)

        if not appointment:
            raise AppointmentNotFoundException()

        AppointmentRepository.delete(db, appointment)

    # ==================== STATS ====================

    @staticmethod
    def get_stats(
        db: Session,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID | None = None,
    ) -> AppointmentStats:
        """Retorna estatísticas de agendamentos."""
        stats = AppointmentRepository.get_stats(db, tenant_id, employee_id)

        return AppointmentStats(**stats)

    # ==================== HELPERS ====================

    @staticmethod
    def _to_response(appointment: Appointment) -> AppointmentResponse:
        """Converte model para schema de resposta."""
        return AppointmentResponse(
            id=appointment.id,
            title=appointment.title,
            description=appointment.description,
            start_datetime=appointment.start_datetime,
            end_datetime=appointment.end_datetime,
            status=AppointmentStatus(appointment.status),
            source=AppointmentSource(appointment.source),
            tenant_id=appointment.tenant_id,
            employee_id=appointment.employee_id,
            lead_id=appointment.lead_id,
            created_by_id=appointment.created_by_id,
            client_name=appointment.client_name,
            client_phone=appointment.client_phone,
            notes=appointment.notes,
            location=appointment.location,
            created_at=appointment.created_at,
            updated_at=appointment.updated_at,
            cancelled_at=appointment.cancelled_at,
            completed_at=appointment.completed_at,
            employee_name=appointment.employee.full_name if appointment.employee else None,
            lead_name=appointment.lead.name if appointment.lead else None,
        )

    @staticmethod
    def _to_calendar_event(appointment: Appointment) -> CalendarEvent:
        """Converte model para formato do FullCalendar."""
        # Cores baseadas na origem
        colors = {
            AppointmentSource.AI.value: {"bg": "#8b5cf6", "border": "#7c3aed"},        # Roxo (IA)
            AppointmentSource.HUMAN_APP.value: {"bg": "#3b82f6", "border": "#2563eb"},  # Azul
            AppointmentSource.HUMAN_ADMIN.value: {"bg": "#10b981", "border": "#059669"}, # Verde
            AppointmentSource.WHATSAPP.value: {"bg": "#22c55e", "border": "#16a34a"},   # Verde WhatsApp
        }

        color = colors.get(appointment.source, colors[AppointmentSource.HUMAN_APP.value])

        # Se cancelado, fica cinza
        if appointment.status == AppointmentStatus.CANCELLED.value:
            color = {"bg": "#9ca3af", "border": "#6b7280"}

        # Se concluído, fica verde mais escuro
        if appointment.status == AppointmentStatus.COMPLETED.value:
            color = {"bg": "#059669", "border": "#047857"}

        return CalendarEvent(
            id=str(appointment.id),
            title=appointment.title,
            start=appointment.start_datetime.isoformat(),
            end=appointment.end_datetime.isoformat(),
            backgroundColor=color["bg"],
            borderColor=color["border"],
            textColor="#ffffff",
            extendedProps={
                "status": appointment.status,
                "source": appointment.source,
                "client_name": appointment.client_name,
                "client_phone": appointment.client_phone,
                "notes": appointment.notes,
                "location": appointment.location,
                "lead_id": str(appointment.lead_id) if appointment.lead_id else None,
                "employee_id": str(appointment.employee_id),
            },
        )
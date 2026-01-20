"""
Repository - Queries isoladas do banco de dados para Appointments.
Não contém lógica de negócio, apenas CRUD.

USO:
    from app.modules.appointments.repository import AppointmentRepository

    appointments = AppointmentRepository.get_by_employee(db, tenant_id, employee_id, start, end)
"""
import uuid
from datetime import datetime, date, time, timedelta
from typing import Sequence

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from app.modules.appointments.models import Appointment, AppointmentStatus, AppointmentSource
from app.modules.appointments.schemas import AppointmentCreate, AppointmentUpdate, AppointmentCreateByAI


class AppointmentRepository:
    """
    Repositório de Appointments.
    Métodos estáticos para queries no banco.
    """

    # ==================== READ ====================

    @staticmethod
    def get_by_id(
        db: Session,
        appointment_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Appointment | None:
        """Busca agendamento por ID dentro do tenant."""
        stmt = select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == tenant_id,
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_all(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        employee_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        status: AppointmentStatus | None = None,
        source: AppointmentSource | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Appointment]:
        """Lista agendamentos com filtros."""
        stmt = select(Appointment).where(Appointment.tenant_id == tenant_id)

        if employee_id:
            stmt = stmt.where(Appointment.employee_id == employee_id)
        if start_date:
            stmt = stmt.where(Appointment.start_datetime >= start_date)
        if end_date:
            stmt = stmt.where(Appointment.start_datetime <= end_date)
        if status:
            stmt = stmt.where(Appointment.status == status.value)
        if source:
            stmt = stmt.where(Appointment.source == source.value)

        stmt = stmt.order_by(Appointment.start_datetime.asc())
        stmt = stmt.offset(skip).limit(limit)

        return db.execute(stmt).scalars().all()

    @staticmethod
    def get_by_employee(
        db: Session,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> Sequence[Appointment]:
        """
        Busca agendamentos de um funcionário específico.
        Exclui cancelados para exibição na agenda.
        """
        stmt = select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.employee_id == employee_id,
            Appointment.start_datetime >= start_date,
            Appointment.start_datetime <= end_date,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        ).order_by(Appointment.start_datetime.asc())

        return db.execute(stmt).scalars().all()

    @staticmethod
    def get_booked_slots(
        db: Session,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        target_date: date,
    ) -> Sequence[Appointment]:
        """Retorna horários já ocupados em um dia específico."""
        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)

        stmt = select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.employee_id == employee_id,
            Appointment.start_datetime >= start_of_day,
            Appointment.start_datetime <= end_of_day,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        ).order_by(Appointment.start_datetime.asc())

        return db.execute(stmt).scalars().all()

    @staticmethod
    def check_conflict(
        db: Session,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID,
        start_datetime: datetime,
        end_datetime: datetime,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """Verifica se há conflito de horário para o funcionário."""
        stmt = select(Appointment.id).where(
            Appointment.tenant_id == tenant_id,
            Appointment.employee_id == employee_id,
            Appointment.status != AppointmentStatus.CANCELLED.value,
            # Verifica sobreposição de horários
            or_(
                # Caso 1: Novo agendamento começa durante um existente
                and_(
                    Appointment.start_datetime <= start_datetime,
                    Appointment.end_datetime > start_datetime,
                ),
                # Caso 2: Novo agendamento termina durante um existente
                and_(
                    Appointment.start_datetime < end_datetime,
                    Appointment.end_datetime >= end_datetime,
                ),
                # Caso 3: Novo agendamento engloba um existente
                and_(
                    Appointment.start_datetime >= start_datetime,
                    Appointment.end_datetime <= end_datetime,
                ),
            ),
        )

        if exclude_id:
            stmt = stmt.where(Appointment.id != exclude_id)

        result = db.execute(stmt).scalar_one_or_none()
        return result is not None

    @staticmethod
    def count(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        employee_id: uuid.UUID | None = None,
        status: AppointmentStatus | None = None,
    ) -> int:
        """Conta total de agendamentos."""
        stmt = select(func.count(Appointment.id)).where(
            Appointment.tenant_id == tenant_id
        )

        if employee_id:
            stmt = stmt.where(Appointment.employee_id == employee_id)
        if status:
            stmt = stmt.where(Appointment.status == status.value)

        return db.execute(stmt).scalar_one()

    # ==================== CREATE ====================

    @staticmethod
    def create(
        db: Session,
        tenant_id: uuid.UUID,
        data: AppointmentCreate,
        created_by_id: uuid.UUID | None = None,
    ) -> Appointment:
        """Cria novo agendamento."""
        appointment = Appointment(
            tenant_id=tenant_id,
            title=data.title,
            description=data.description,
            start_datetime=data.start_datetime,
            end_datetime=data.end_datetime,
            employee_id=data.employee_id,
            lead_id=data.lead_id,
            client_name=data.client_name,
            client_phone=data.client_phone,
            notes=data.notes,
            location=data.location,
            source=data.source.value,
            created_by_id=created_by_id,
        )

        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        return appointment

    @staticmethod
    def create_by_ai(
        db: Session,
        tenant_id: uuid.UUID,
        data: AppointmentCreateByAI,
    ) -> Appointment:
        """Cria agendamento via IA (sempre source=AI e status=CONFIRMED)."""
        appointment = Appointment(
            tenant_id=tenant_id,
            title=data.title,
            start_datetime=data.start_datetime,
            end_datetime=data.end_datetime,
            employee_id=data.employee_id,
            lead_id=data.lead_id,
            client_name=data.client_name,
            client_phone=data.client_phone,
            notes=data.notes,
            location=data.location,
            source=AppointmentSource.AI.value,
            status=AppointmentStatus.CONFIRMED.value,  # IA já confirma
        )

        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        return appointment

    # ==================== UPDATE ====================

    @staticmethod
    def update(
        db: Session,
        appointment: Appointment,
        data: AppointmentUpdate,
    ) -> Appointment:
        """Atualiza agendamento existente."""
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "status" and value:
                setattr(appointment, field, value.value)
            else:
                setattr(appointment, field, value)

        db.commit()
        db.refresh(appointment)

        return appointment

    @staticmethod
    def cancel(db: Session, appointment: Appointment) -> Appointment:
        """Cancela um agendamento."""
        appointment.status = AppointmentStatus.CANCELLED.value
        appointment.cancelled_at = datetime.utcnow()

        db.commit()
        db.refresh(appointment)

        return appointment

    @staticmethod
    def confirm(db: Session, appointment: Appointment) -> Appointment:
        """Confirma um agendamento pendente."""
        appointment.status = AppointmentStatus.CONFIRMED.value

        db.commit()
        db.refresh(appointment)

        return appointment

    @staticmethod
    def complete(db: Session, appointment: Appointment) -> Appointment:
        """Marca agendamento como concluído."""
        appointment.status = AppointmentStatus.COMPLETED.value
        appointment.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(appointment)

        return appointment

    @staticmethod
    def mark_no_show(db: Session, appointment: Appointment) -> Appointment:
        """Marca agendamento como no-show (cliente não compareceu)."""
        appointment.status = AppointmentStatus.NO_SHOW.value

        db.commit()
        db.refresh(appointment)

        return appointment

    # ==================== DELETE ====================

    @staticmethod
    def delete(db: Session, appointment: Appointment) -> None:
        """Remove agendamento do banco."""
        db.delete(appointment)
        db.commit()

    # ==================== STATS ====================

    @staticmethod
    def get_stats(
        db: Session,
        tenant_id: uuid.UUID,
        employee_id: uuid.UUID | None = None,
    ) -> dict:
        """Retorna estatísticas de agendamentos."""
        base_stmt = select(Appointment).where(Appointment.tenant_id == tenant_id)

        if employee_id:
            base_stmt = base_stmt.where(Appointment.employee_id == employee_id)

        appointments = db.execute(base_stmt).scalars().all()

        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Contagem por status
        by_status = {}
        for status in AppointmentStatus:
            count = sum(1 for a in appointments if a.status == status.value)
            by_status[status.value] = count

        # Contagem por origem
        by_source = {}
        for source in AppointmentSource:
            count = sum(1 for a in appointments if a.source == source.value)
            by_source[source.value] = count

        return {
            "total": len(appointments),
            "by_status": by_status,
            "by_source": by_source,
            "today": sum(1 for a in appointments if a.start_datetime.date() == today),
            "this_week": sum(1 for a in appointments if a.start_datetime.date() >= week_start),
            "this_month": sum(1 for a in appointments if a.start_datetime.date() >= month_start),
        }
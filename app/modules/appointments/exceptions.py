"""
Exceções customizadas do módulo Appointments.

USO:
    from app.modules.appointments.exceptions import AppointmentNotFoundException

    if not appointment:
        raise AppointmentNotFoundException()
"""
from fastapi import HTTPException, status


class AppointmentNotFoundException(HTTPException):
    """Agendamento não encontrado."""

    def __init__(self, detail: str = "Agendamento não encontrado"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class AppointmentConflictException(HTTPException):
    """Conflito de horário."""

    def __init__(self, detail: str = "Já existe um agendamento neste horário"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class InvalidDateRangeException(HTTPException):
    """Data/hora inválida."""

    def __init__(self, detail: str = "Data/hora de término deve ser após o início"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class PastDateException(HTTPException):
    """Tentativa de agendar em data passada."""

    def __init__(self, detail: str = "Não é possível agendar em datas passadas"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class EmployeeNotFoundException(HTTPException):
    """Funcionário não encontrado."""

    def __init__(self, detail: str = "Funcionário não encontrado"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class AppointmentCannotBeModifiedException(HTTPException):
    """Agendamento não pode ser modificado (já cancelado/concluído)."""

    def __init__(self, detail: str = "Este agendamento não pode ser modificado"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
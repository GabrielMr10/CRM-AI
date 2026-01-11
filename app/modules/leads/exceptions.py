"""
Exceções específicas do módulo Leads.
"""
from app.core.exceptions import NotFoundException, ConflictException


class LeadNotFoundError(NotFoundException):
    def __init__(self, lead_id: str | None = None):
        detail = "Lead não encontrado"
        if lead_id:
            detail = f"Lead '{lead_id}' não encontrado"
        super().__init__(detail=detail)


class LeadPhoneExistsError(ConflictException):
    def __init__(self, phone: str):
        super().__init__(detail=f"Já existe um lead com o telefone '{phone}'")


class LeadEmailExistsError(ConflictException):
    def __init__(self, email: str):
        super().__init__(detail=f"Já existe um lead com o email '{email}'")
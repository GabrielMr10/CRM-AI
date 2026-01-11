"""
Exceções do módulo Webhooks.
"""
from app.core.exceptions import BadRequestException, UnauthorizedException


class InvalidWebhookPayloadError(BadRequestException):
    def __init__(self, detail: str = "Payload inválido"):
        super().__init__(detail=detail)


class WebhookAuthenticationError(UnauthorizedException):
    def __init__(self):
        super().__init__(detail="Token de webhook inválido")


class TenantNotConfiguredError(BadRequestException):
    def __init__(self, tenant_id: str):
        super().__init__(detail=f"Tenant '{tenant_id}' não configurado para webhooks")
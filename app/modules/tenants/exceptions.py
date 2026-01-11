"""
Exceções específicas do módulo Tenants.

USO:
    from app.modules.tenants.exceptions import TenantNotFoundError
    
    if not tenant:
        raise TenantNotFoundError()
"""
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    ForbiddenException,
)


class TenantNotFoundError(NotFoundException):
    """Tenant não encontrado."""
    
    def __init__(self, tenant_id: str | None = None):
        detail = "Tenant não encontrado"
        if tenant_id:
            detail = f"Tenant '{tenant_id}' não encontrado"
        super().__init__(detail=detail)


class TenantSlugExistsError(ConflictException):
    """Slug já está em uso."""
    
    def __init__(self, slug: str):
        super().__init__(detail=f"Slug '{slug}' já está em uso")


class TenantEmailExistsError(ConflictException):
    """Email já está em uso."""
    
    def __init__(self, email: str):
        super().__init__(detail=f"Email '{email}' já está cadastrado")


class TenantInactiveError(ForbiddenException):
    """Tenant está inativo."""
    
    def __init__(self):
        super().__init__(detail="Tenant está suspenso. Entre em contato com o suporte.")


class TenantLimitReachedError(ForbiddenException):
    """Limite do plano atingido."""
    
    def __init__(self, resource: str):
        super().__init__(detail=f"Limite de {resource} atingido para seu plano")
"""
Dependencies específicas do módulo Tenants.

USO:
    from app.modules.tenants.dependencies import get_current_tenant
    
    @router.get("/leads")
    def list_leads(tenant: Tenant = Depends(get_current_tenant)):
        # tenant já validado e ativo
        ...
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.modules.tenants.models import Tenant
from app.modules.tenants.service import TenantService


async def get_current_tenant(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
) -> Tenant:
    """
    Obtém tenant do usuário logado.
    Valida se tenant está ativo.
    
    Fluxo:
        1. get_current_user extrai user do JWT
        2. User tem tenant_id
        3. Busca tenant e valida se ativo
    
    Raises:
        TenantNotFoundError: Se tenant não existe
        TenantInactiveError: Se tenant inativo
    """
    return TenantService.get_active_or_403(db, current_user.tenant_id)


# Type alias para uso mais limpo
CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]
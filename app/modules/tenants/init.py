"""
Tenants Module - Multi-tenancy
Gerencia empresas/clientes do SaaS.
"""
from app.modules.tenants.models import Tenant
from app.modules.tenants.schemas import TenantCreate, TenantUpdate, TenantResponse
from app.modules.tenants.service import TenantService
from app.modules.tenants.dependencies import get_current_tenant

__all__ = [
    "Tenant",
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "TenantService",
    "get_current_tenant",
]
"""
Validação de segurança dos webhooks.
"""
import hmac
import hashlib
from fastapi import Request, Header, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.modules.webhooks.exceptions import WebhookAuthenticationError, TenantNotConfiguredError
from app.modules.tenants.repository import TenantRepository


async def verify_zapi_webhook(
    request: Request,
    x_zapi_token: str | None = Header(None, alias="X-ZAPI-TOKEN"),
    x_instance_id: str | None = Header(None, alias="X-Instance-Id"),
) -> dict:
    """
    Verifica autenticidade do webhook Z-API.
    
    Retorna dict com tenant_id se válido.
    """
    # Por enquanto, aceita qualquer request
    # Em produção, validar token configurado no tenant
    
    return {
        "instance_id": x_instance_id,
        "token": x_zapi_token,
    }


async def verify_n8n_webhook(
    request: Request,
    x_webhook_token: str | None = Header(None, alias="X-Webhook-Token"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-Id"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Verifica autenticidade do webhook n8n.
    
    Cada tenant tem um token único para webhooks.
    """
    if not x_tenant_id:
        raise WebhookAuthenticationError()
    
    # Buscar tenant
    from uuid import UUID
    try:
        tenant = TenantRepository.get_by_id(db, UUID(x_tenant_id))
    except ValueError:
        raise TenantNotConfiguredError(x_tenant_id)
    
    if not tenant:
        raise TenantNotConfiguredError(x_tenant_id)
    
    # Validar token (armazenado em tenant.settings)
    expected_token = tenant.get_setting("webhook_token")
    
    if expected_token and x_webhook_token != expected_token:
        raise WebhookAuthenticationError()
    
    return {
        "tenant_id": tenant.id,
        "tenant": tenant,
    }
"""
Router - Endpoints HTTP do módulo Tenants.

Prefixo: /api/v1/tenants
Tags: ["Tenants"]

USO no main.py:
    from app.modules.tenants.router import router as tenants_router
    app.include_router(tenants_router, prefix="/api/v1/tenants", tags=["Tenants"])
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user, get_current_active_superuser
from app.modules.tenants.schemas import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
)
from app.modules.tenants.service import TenantService
from app.modules.tenants.dependencies import get_current_tenant, CurrentTenant

router = APIRouter()


# ==================== PÚBLICO ====================

@router.post(
    "/",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo tenant",
    description="Cria um novo tenant (empresa). Usado no signup.",
)
def create_tenant(
    data: TenantCreate,
    db: Session = Depends(get_db),
):
    """
    Cria novo tenant.
    
    - **name**: Nome da empresa (obrigatório)
    - **email**: Email de contato (obrigatório, único)
    - **slug**: Identificador único (opcional, gerado do nome)
    - **phone**: Telefone (opcional)
    - **document**: CNPJ/CPF (opcional)
    """
    tenant = TenantService.create(db, data=data)
    return tenant


# ==================== AUTENTICADO (PRÓPRIO TENANT) ====================

@router.get(
    "/me",
    response_model=TenantResponse,
    summary="Dados do tenant atual",
)
def get_my_tenant(
    tenant: CurrentTenant,
):
    """Retorna dados do tenant do usuário logado."""
    return tenant


@router.patch(
    "/me",
    response_model=TenantResponse,
    summary="Atualizar meu tenant",
)
def update_my_tenant(
    data: TenantUpdate,
    tenant: CurrentTenant,
    db: Session = Depends(get_db),
):
    """
    Atualiza dados do tenant do usuário logado.
    Apenas campos enviados são atualizados.
    """
    return TenantService.update(db, tenant_id=tenant.id, data=data)


# ==================== SUPERUSER ONLY ====================

@router.get(
    "/",
    response_model=TenantListResponse,
    summary="Listar todos tenants",
    description="Apenas superusuários podem listar todos os tenants.",
)
def list_tenants(
    db: Session = Depends(get_db),
    _: any = Depends(get_current_active_superuser),
    page: Annotated[int, Query(ge=1, description="Página")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Itens por página")] = 20,
    is_active: Annotated[bool | None, Query(description="Filtrar por status")] = None,
):
    """Lista todos os tenants com paginação."""
    return TenantService.list_paginated(
        db,
        page=page,
        per_page=per_page,
        is_active=is_active,
    )


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Detalhe de um tenant",
)
def get_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: any = Depends(get_current_active_superuser),
):
    """Retorna detalhes de um tenant específico."""
    return TenantService.get_or_404(db, tenant_id)


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar tenant",
    description="Remove permanentemente um tenant e TODOS os seus dados.",
)
def delete_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: any = Depends(get_current_active_superuser),
):
    """
    Remove tenant permanentemente.
    
    ⚠️ CUIDADO: Esta ação é irreversível e remove todos os dados do tenant.
    """
    TenantService.delete(db, tenant_id=tenant_id)
    return None


@router.post(
    "/{tenant_id}/deactivate",
    response_model=TenantResponse,
    summary="Desativar tenant",
)
def deactivate_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: any = Depends(get_current_active_superuser),
):
    """
    Desativa tenant (soft delete).
    Dados são mantidos mas tenant não pode operar.
    """
    return TenantService.deactivate(db, tenant_id=tenant_id)


@router.post(
    "/{tenant_id}/activate",
    response_model=TenantResponse,
    summary="Reativar tenant",
)
def activate_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: any = Depends(get_current_active_superuser),
):
    """Reativa um tenant previamente desativado."""
    from app.modules.tenants.schemas import TenantUpdate
    return TenantService.update(
        db,
        tenant_id=tenant_id,
        data=TenantUpdate(is_active=True),  # type: ignore
    )
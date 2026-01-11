"""
Router - Endpoints HTTP do módulo Leads.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.modules.leads.models import LeadStatus, LeadSource
from app.modules.leads.schemas import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
)
from app.modules.leads.service import LeadService
from app.modules.leads.filters import LeadFilters
from app.modules.tenants.dependencies import get_current_tenant, CurrentTenant
from app.modules.users.models import User

router = APIRouter()


@router.get(
    "/",
    response_model=LeadListResponse,
    summary="Listar leads",
)
def list_leads(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
    status: LeadStatus | None = None,
    source: LeadSource | None = None,
    assigned_to_id: uuid.UUID | None = None,
    temperature: str | None = None,
    tag: str | None = None,
    city: str | None = None,
    state: str | None = None,
):
    """Lista leads do tenant com filtros."""
    filters = LeadFilters(
        search=search,
        status=status,
        source=source,
        assigned_to_id=str(assigned_to_id) if assigned_to_id else None,
        temperature=temperature,
        tag=tag,
        city=city,
        state=state,
    )
    
    return LeadService.list_paginated(
        db,
        tenant.id,
        page=page,
        per_page=per_page,
        filters=filters,
    )


@router.post(
    "/",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar lead",
)
def create_lead(
    data: LeadCreate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Cria novo lead."""
    return LeadService.create(
        db,
        data=data,
        tenant_id=tenant.id,
        created_by=current_user,
    )


@router.get(
    "/stats",
    summary="Estatísticas de leads",
)
def get_lead_stats(
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Retorna estatísticas para dashboard."""
    return LeadService.get_stats(db, tenant.id)


@router.get(
    "/by-phone/{phone}",
    response_model=LeadResponse | None,
    summary="Buscar por telefone",
)
def get_lead_by_phone(
    phone: str,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Busca lead pelo telefone."""
    return LeadService.get_by_phone(db, phone, tenant.id)


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Detalhe do lead",
)
def get_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Retorna detalhes de um lead."""
    return LeadService.get_or_404(db, lead_id, tenant.id)


@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Atualizar lead",
)
def update_lead(
    lead_id: uuid.UUID,
    data: LeadUpdate,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Atualiza dados do lead."""
    return LeadService.update(
        db,
        lead_id=lead_id,
        tenant_id=tenant.id,
        data=data,
    )


@router.patch(
    "/{lead_id}/status",
    response_model=LeadResponse,
    summary="Alterar status",
)
def change_lead_status(
    lead_id: uuid.UUID,
    status: LeadStatus,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Altera status do lead no funil."""
    return LeadService.change_status(
        db,
        lead_id=lead_id,
        tenant_id=tenant.id,
        status=status,
    )


@router.patch(
    "/{lead_id}/assign",
    response_model=LeadResponse,
    summary="Atribuir responsável",
)
def assign_lead(
    lead_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Atribui lead a um usuário."""
    return LeadService.assign(
        db,
        lead_id=lead_id,
        tenant_id=tenant.id,
        user_id=user_id,
    )


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar lead",
)
def delete_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: CurrentTenant = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Remove lead."""
    LeadService.delete(db, lead_id=lead_id, tenant_id=tenant.id)
    return None
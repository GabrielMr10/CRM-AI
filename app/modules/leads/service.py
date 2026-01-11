"""
Service - Lógica de negócio.
"""
import uuid
from math import ceil

from sqlalchemy.orm import Session

from app.modules.leads.models import Lead, LeadStatus
from app.modules.leads.schemas import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
)
from app.modules.leads.repository import LeadRepository
from app.modules.leads.filters import LeadFilters
from app.modules.leads.exceptions import (
    LeadNotFoundError,
    LeadPhoneExistsError,
)
from app.modules.users.models import User


class LeadService:
    
    @staticmethod
    def get_or_404(
        db: Session,
        lead_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Lead:
        lead = LeadRepository.get_by_id_and_tenant(db, lead_id, tenant_id)
        if not lead:
            raise LeadNotFoundError(str(lead_id))
        return lead
    
    @staticmethod
    def get_by_phone(
        db: Session,
        phone: str,
        tenant_id: uuid.UUID,
    ) -> Lead | None:
        return LeadRepository.get_by_phone(db, phone, tenant_id)
    
    @staticmethod
    def list_paginated(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
        filters: LeadFilters | None = None,
    ) -> LeadListResponse:
        skip = (page - 1) * per_page
        
        leads = LeadRepository.get_all(
            db,
            tenant_id,
            skip=skip,
            limit=per_page,
            filters=filters,
        )
        
        total = LeadRepository.count(db, tenant_id, filters=filters)
        pages = ceil(total / per_page) if total > 0 else 1
        
        return LeadListResponse(
            items=[LeadResponse.model_validate(l) for l in leads],
            total=total,
            page=page,
            pages=pages,
            per_page=per_page,
        )
    
    @staticmethod
    def create(
        db: Session,
        *,
        data: LeadCreate,
        tenant_id: uuid.UUID,
        created_by: User | None = None,
    ) -> Lead:
        # Verificar telefone duplicado
        if LeadRepository.exists_phone(db, data.phone, tenant_id):
            raise LeadPhoneExistsError(data.phone)
        
        return LeadRepository.create(
            db,
            data=data,
            tenant_id=tenant_id,
            created_by_id=created_by.id if created_by else None,
        )
    
    @staticmethod
    def create_or_get(
        db: Session,
        *,
        data: LeadCreate,
        tenant_id: uuid.UUID,
        created_by: User | None = None,
    ) -> tuple[Lead, bool]:
        """
        Cria lead ou retorna existente pelo telefone.
        Retorna: (lead, criado: bool)
        """
        existing = LeadRepository.get_by_phone(db, data.phone, tenant_id)
        
        if existing:
            return existing, False
        
        lead = LeadRepository.create(
            db,
            data=data,
            tenant_id=tenant_id,
            created_by_id=created_by.id if created_by else None,
        )
        
        return lead, True
    
    @staticmethod
    def update(
        db: Session,
        *,
        lead_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: LeadUpdate,
    ) -> Lead:
        lead = LeadService.get_or_404(db, lead_id, tenant_id)
        
        # Verificar telefone duplicado se alterado
        if data.phone and data.phone != lead.phone:
            if LeadRepository.exists_phone(db, data.phone, tenant_id, exclude_id=lead_id):
                raise LeadPhoneExistsError(data.phone)
        
        return LeadRepository.update(db, lead=lead, data=data)
    
    @staticmethod
    def change_status(
        db: Session,
        *,
        lead_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: LeadStatus,
    ) -> Lead:
        lead = LeadService.get_or_404(db, lead_id, tenant_id)
        return LeadRepository.update_status(db, lead=lead, status=status.value)
    
    @staticmethod
    def assign(
        db: Session,
        *,
        lead_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
    ) -> Lead:
        lead = LeadService.get_or_404(db, lead_id, tenant_id)
        lead.assigned_to_id = user_id
        db.commit()
        db.refresh(lead)
        return lead
    
    @staticmethod
    def delete(
        db: Session,
        *,
        lead_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        lead = LeadService.get_or_404(db, lead_id, tenant_id)
        LeadRepository.delete(db, lead=lead)
    
    @staticmethod
    def get_stats(db: Session, tenant_id: uuid.UUID) -> dict:
        """Estatísticas para dashboard."""
        by_status = LeadRepository.count_by_status(db, tenant_id)
        total = sum(by_status.values())
        
        return {
            "total": total,
            "by_status": by_status,
            "conversion_rate": (
                round(by_status.get("won", 0) / total * 100, 2)
                if total > 0 else 0
            ),
        }
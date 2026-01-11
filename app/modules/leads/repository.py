"""
Repository - Queries do banco de dados.
"""
import uuid
from typing import Sequence
from datetime import datetime, timezone

from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session

from app.modules.leads.models import Lead
from app.modules.leads.schemas import LeadCreate, LeadUpdate
from app.modules.leads.filters import LeadFilters


class LeadRepository:
    
    @staticmethod
    def get_by_id(db: Session, lead_id: uuid.UUID) -> Lead | None:
        return db.get(Lead, lead_id)
    
    @staticmethod
    def get_by_id_and_tenant(
        db: Session,
        lead_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Lead | None:
        stmt = select(Lead).where(
            and_(Lead.id == lead_id, Lead.tenant_id == tenant_id)
        )
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_by_phone(
        db: Session,
        phone: str,
        tenant_id: uuid.UUID,
    ) -> Lead | None:
        stmt = select(Lead).where(
            and_(Lead.phone == phone, Lead.tenant_id == tenant_id)
        )
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_by_email(
        db: Session,
        email: str,
        tenant_id: uuid.UUID,
    ) -> Lead | None:
        stmt = select(Lead).where(
            and_(Lead.email == email, Lead.tenant_id == tenant_id)
        )
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_all(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
        filters: LeadFilters | None = None,
    ) -> Sequence[Lead]:
        stmt = (
            select(Lead)
            .where(Lead.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .order_by(Lead.created_at.desc())
        )
        
        if filters:
            stmt = LeadRepository._apply_filters(stmt, filters)
        
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def count(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        filters: LeadFilters | None = None,
    ) -> int:
        stmt = select(func.count(Lead.id)).where(Lead.tenant_id == tenant_id)
        
        if filters:
            stmt = LeadRepository._apply_filters(stmt, filters)
        
        return db.execute(stmt).scalar_one()
    
    @staticmethod
    def _apply_filters(stmt, filters: LeadFilters):
        """Aplica filtros à query."""
        
        if filters.search:
            search = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    Lead.name.ilike(search),
                    Lead.email.ilike(search),
                    Lead.phone.ilike(search),
                    Lead.company_name.ilike(search),
                )
            )
        
        if filters.status:
            stmt = stmt.where(Lead.status == filters.status.value)
        
        if filters.source:
            stmt = stmt.where(Lead.source == filters.source.value)
        
        if filters.assigned_to_id:
            stmt = stmt.where(Lead.assigned_to_id == uuid.UUID(filters.assigned_to_id))
        
        if filters.temperature:
            stmt = stmt.where(Lead.temperature == filters.temperature)
        
        if filters.tag:
            stmt = stmt.where(Lead.tags.contains([filters.tag]))
        
        if filters.has_email is True:
            stmt = stmt.where(Lead.email.isnot(None))
        elif filters.has_email is False:
            stmt = stmt.where(Lead.email.is_(None))
        
        if filters.city:
            stmt = stmt.where(Lead.address_city.ilike(f"%{filters.city}%"))
        
        if filters.state:
            stmt = stmt.where(Lead.address_state == filters.state.upper())
        
        if filters.min_score is not None:
            stmt = stmt.where(Lead.score >= filters.min_score)
        
        if filters.max_score is not None:
            stmt = stmt.where(Lead.score <= filters.max_score)
        
        return stmt
    
    @staticmethod
    def exists_phone(
        db: Session,
        phone: str,
        tenant_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        stmt = select(Lead.id).where(
            and_(Lead.phone == phone, Lead.tenant_id == tenant_id)
        )
        if exclude_id:
            stmt = stmt.where(Lead.id != exclude_id)
        return db.execute(stmt).scalar_one_or_none() is not None
    
    @staticmethod
    def create(
        db: Session,
        *,
        data: LeadCreate,
        tenant_id: uuid.UUID,
        created_by_id: uuid.UUID | None = None,
    ) -> Lead:
        lead = Lead(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by_id=created_by_id,
        )
        
        db.add(lead)
        db.commit()
        db.refresh(lead)
        
        return lead
    
    @staticmethod
    def update(db: Session, *, lead: Lead, data: LeadUpdate) -> Lead:
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(lead, field, value)
        
        db.commit()
        db.refresh(lead)
        
        return lead
    
    @staticmethod
    def update_status(db: Session, *, lead: Lead, status: str) -> Lead:
        lead.status = status
        
        if status == "won":
            lead.converted_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(lead)
        
        return lead
    
    @staticmethod
    def update_last_contact(db: Session, *, lead: Lead) -> Lead:
        lead.last_contact_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(lead)
        return lead
    
    @staticmethod
    def delete(db: Session, *, lead: Lead) -> None:
        db.delete(lead)
        db.commit()
    
    @staticmethod
    def count_by_status(
        db: Session,
        tenant_id: uuid.UUID,
    ) -> dict[str, int]:
        """Conta leads por status (para dashboard)."""
        stmt = (
            select(Lead.status, func.count(Lead.id))
            .where(Lead.tenant_id == tenant_id)
            .group_by(Lead.status)
        )
        results = db.execute(stmt).all()
        return {status: count for status, count in results}
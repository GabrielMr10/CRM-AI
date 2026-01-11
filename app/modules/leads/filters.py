"""
Filtros de busca para Leads.
"""
from pydantic import BaseModel, Field
from app.modules.leads.models import LeadStatus, LeadSource


class LeadFilters(BaseModel):
    """Filtros disponíveis para listagem de leads."""
    
    search: str | None = Field(None, description="Busca por nome, email ou telefone")
    status: LeadStatus | None = None
    source: LeadSource | None = None
    assigned_to_id: str | None = None
    temperature: str | None = None
    tag: str | None = None
    has_email: bool | None = None
    city: str | None = None
    state: str | None = None
    min_score: int | None = Field(None, ge=0, le=100)
    max_score: int | None = Field(None, ge=0, le=100)
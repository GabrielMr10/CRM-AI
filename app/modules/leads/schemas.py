"""
Schemas Pydantic para Leads.
"""
import uuid
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from app.modules.leads.models import LeadStatus, LeadSource


class LeadBase(BaseModel):
    """Campos base do Lead."""
    
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str = Field(..., min_length=10, max_length=20)
    phone_secondary: str | None = Field(None, max_length=20)
    document: str | None = Field(None, max_length=20)
    
    # Empresa
    company_name: str | None = Field(None, max_length=255)
    company_position: str | None = Field(None, max_length=100)
    
    # Endereço
    address_street: str | None = Field(None, max_length=255)
    address_number: str | None = Field(None, max_length=20)
    address_complement: str | None = Field(None, max_length=100)
    address_neighborhood: str | None = Field(None, max_length=100)
    address_city: str | None = Field(None, max_length=100)
    address_state: str | None = Field(None, max_length=2)
    address_zipcode: str | None = Field(None, max_length=10)
    
    # Qualificação
    interest: str | None = Field(None, max_length=255)
    budget: float | None = None
    notes: str | None = None
    
    @field_validator("phone", "phone_secondary", mode="before")
    @classmethod
    def clean_phone(cls, v):
        if v:
            return re.sub(r"\D", "", v)
        return v
    
    @field_validator("document", mode="before")
    @classmethod
    def clean_document(cls, v):
        if v:
            return re.sub(r"\D", "", v)
        return v
    
    @field_validator("address_zipcode", mode="before")
    @classmethod
    def clean_zipcode(cls, v):
        if v:
            return re.sub(r"\D", "", v)
        return v


class LeadCreate(LeadBase):
    """Schema para criação."""
    
    source: LeadSource = Field(default=LeadSource.MANUAL)
    source_detail: str | None = None
    status: LeadStatus = Field(default=LeadStatus.NEW)
    assigned_to_id: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class LeadUpdate(BaseModel):
    """Schema para atualização parcial."""
    
    name: str | None = Field(None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, min_length=10, max_length=20)
    phone_secondary: str | None = None
    document: str | None = None
    
    company_name: str | None = None
    company_position: str | None = None
    
    address_street: str | None = None
    address_number: str | None = None
    address_complement: str | None = None
    address_neighborhood: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_zipcode: str | None = None
    
    status: LeadStatus | None = None
    source: LeadSource | None = None
    source_detail: str | None = None
    
    score: int | None = Field(None, ge=0, le=100)
    temperature: str | None = None
    interest: str | None = None
    budget: float | None = None
    notes: str | None = None
    
    assigned_to_id: uuid.UUID | None = None
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None
    
    @field_validator("phone", "phone_secondary", mode="before")
    @classmethod
    def clean_phone(cls, v):
        if v:
            return re.sub(r"\D", "", v)
        return v


class LeadResponse(BaseModel):
    """Schema de resposta."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    email: str | None
    phone: str
    phone_secondary: str | None
    document: str | None
    
    company_name: str | None
    company_position: str | None
    
    address_street: str | None
    address_number: str | None
    address_complement: str | None
    address_neighborhood: str | None
    address_city: str | None
    address_state: str | None
    address_zipcode: str | None
    
    status: str
    source: str
    source_detail: str | None
    
    score: int
    temperature: str | None
    interest: str | None
    budget: float | None
    notes: str | None
    
    tags: list[str]
    custom_fields: dict[str, Any]
    
    tenant_id: uuid.UUID
    assigned_to_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    
    created_at: datetime
    updated_at: datetime
    last_contact_at: datetime | None
    converted_at: datetime | None


class LeadListResponse(BaseModel):
    """Schema para listagem com paginação."""
    
    items: list[LeadResponse]
    total: int
    page: int
    pages: int
    per_page: int


class LeadMinimal(BaseModel):
    """Schema mínimo para referências."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    phone: str
    status: str
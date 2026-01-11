"""
Schemas Pydantic para Leads
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.modules.lead import LeadStatus


class LeadBase(BaseModel):
    """Schema base de lead"""
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: LeadStatus = LeadStatus.NEW
    notes: Optional[str] = None


class LeadCreate(LeadBase):
    """Schema para criação de lead"""
    pass


class LeadUpdate(BaseModel):
    """Schema para atualização de lead"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None


class LeadResponse(LeadBase):
    """Schema de resposta de lead"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


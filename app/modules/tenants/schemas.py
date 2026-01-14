"""
Schemas Pydantic para validação de request/response.

USO:
    from app.modules.tenants.schemas import TenantCreate, TenantResponse
    
    # No router:
    @router.post("/", response_model=TenantResponse)
    def create(data: TenantCreate):
        ...
"""
import uuid
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, ConfigDict


# ==================== BASE ====================

class TenantBase(BaseModel):
    """Campos comuns entre Create e Update."""
    
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nome da empresa",
        examples=["Minha Empresa LTDA"],
    )
    
    email: EmailStr = Field(
        ...,
        description="Email principal de contato",
        examples=["contato@empresa.com"],
    )
    
    phone: str | None = Field(
        None,
        max_length=20,
        description="Telefone com DDD",
        examples=["11999998888"],
    )
    
    document: str | None = Field(
        None,
        max_length=20,
        description="CNPJ ou CPF (apenas números)",
        examples=["12345678000199"],
    )


# ==================== CREATE ====================

class TenantCreate(TenantBase):
    """
    Schema para criação de tenant.
    Slug é gerado automaticamente do nome se não informado.
    """
    
    slug: str | None = Field(
        None,
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Identificador único (letras minúsculas, números e hífens)",
        examples=["minha-empresa"],
    )

    @model_validator(mode="after")
    def generate_slug_if_needed(self):
        """Gera slug do nome se não informado."""
        if not self.slug:
            # Pega o nome e gera o slug
            name = self.name
            if name:
                # Remove acentos e caracteres especiais
                slug = name.lower().strip()
                slug = re.sub(r"[àáâãäå]", "a", slug)
                slug = re.sub(r"[èéêë]", "e", slug)
                slug = re.sub(r"[ìíîï]", "i", slug)
                slug = re.sub(r"[òóôõö]", "o", slug)
                slug = re.sub(r"[ùúûü]", "u", slug)
                slug = re.sub(r"[ç]", "c", slug)
                slug = re.sub(r"[^a-z0-9\s-]", "", slug)
                slug = re.sub(r"[\s_]+", "-", slug)
                slug = re.sub(r"-+", "-", slug)
                slug = slug.strip("-")
                self.slug = slug
            else:
                raise ValueError("Nome é obrigatório para gerar slug")
        else:
            self.slug = self.slug.lower().strip()

        return self
    
    @field_validator("document", mode="before")
    @classmethod
    def clean_document(cls, v):
        """Remove formatação do documento."""
        if v:
            return re.sub(r"\D", "", v)
        return v
    
    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, v):
        """Remove formatação do telefone."""
        if v:
            return re.sub(r"\D", "", v)
        return v


# ==================== UPDATE ====================

class TenantUpdate(BaseModel):
    """
    Schema para atualização parcial.
    Todos os campos são opcionais.
    """
    
    name: str | None = Field(None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    document: str | None = Field(None, max_length=20)
    plan: str | None = Field(None, max_length=50)
    settings: dict[str, Any] | None = None
    
    @field_validator("document", "phone", mode="before")
    @classmethod
    def clean_fields(cls, v):
        """Remove formatação."""
        if v:
            return re.sub(r"\D", "", v)
        return v


# ==================== RESPONSE ====================

class TenantResponse(BaseModel):
    """
    Schema de resposta - dados públicos do tenant.
    Não expõe n8n_api_key por segurança.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    slug: str
    email: str
    phone: str | None
    document: str | None
    plan: str
    is_active: bool
    settings: dict[str, Any]
    n8n_instance_url: str | None
    n8n_provisioned: bool
    created_at: datetime
    updated_at: datetime


class TenantListResponse(BaseModel):
    """Schema para listagem com paginação."""
    
    items: list[TenantResponse]
    total: int
    page: int
    pages: int
    per_page: int


# ==================== INTERNOS ====================

class TenantInDB(TenantResponse):
    """Schema interno com todos os campos."""
    
    n8n_api_key: str | None = None
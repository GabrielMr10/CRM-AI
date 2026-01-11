"""
Schemas Pydantic para Users.

USO:
    from app.modules.users.schemas import UserCreate, UserResponse
"""
import uuid
import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from app.modules.users.roles import UserRole


# ==================== BASE ====================

class UserBase(BaseModel):
    """Campos comuns."""
    
    email: EmailStr = Field(
        ...,
        description="Email do usuário",
        examples=["usuario@empresa.com"],
    )
    
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nome completo",
        examples=["João Silva"],
    )
    
    phone: str | None = Field(
        None,
        max_length=20,
        description="Telefone com DDD",
        examples=["11999998888"],
    )
    
    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, v):
        if v:
            return re.sub(r"\D", "", v)
        return v


# ==================== CREATE ====================

class UserCreate(UserBase):
    """Schema para criação de usuário."""
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Senha (mínimo 8 caracteres)",
    )
    
    role: UserRole = Field(
        default=UserRole.MEMBER,
        description="Papel do usuário",
    )
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Valida força da senha."""
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Senha deve conter pelo menos uma letra")
        if not re.search(r"\d", v):
            raise ValueError("Senha deve conter pelo menos um número")
        return v


class UserCreateInternal(UserCreate):
    """Schema interno - inclui tenant_id e hashed_password."""
    
    tenant_id: uuid.UUID
    hashed_password: str
    password: str | None = None  # Não precisa mais


# ==================== UPDATE ====================

class UserUpdate(BaseModel):
    """Schema para atualização parcial."""
    
    full_name: str | None = Field(None, min_length=2, max_length=255)
    phone: str | None = Field(None, max_length=20)
    avatar_url: str | None = Field(None, max_length=500)
    
    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, v):
        if v:
            return re.sub(r"\D", "", v)
        return v


class UserUpdateByAdmin(UserUpdate):
    """Schema para admin atualizar outro usuário."""
    
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserChangePassword(BaseModel):
    """Schema para troca de senha."""
    
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Senha deve conter pelo menos uma letra")
        if not re.search(r"\d", v):
            raise ValueError("Senha deve conter pelo menos um número")
        return v


# ==================== RESPONSE ====================

class UserResponse(BaseModel):
    """Schema de resposta - dados públicos."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    avatar_url: str | None
    role: str
    is_active: bool
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


class UserListResponse(BaseModel):
    """Schema para listagem com paginação."""
    
    items: list[UserResponse]
    total: int
    page: int
    pages: int
    per_page: int


class UserMinimal(BaseModel):
    """Schema mínimo para referências."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    email: str
    full_name: str
    role: str
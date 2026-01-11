"""
Schemas Pydantic para Auth.
"""
import re
from pydantic import BaseModel, EmailStr, Field, field_validator


# ==================== LOGIN ====================

class LoginRequest(BaseModel):
    """Schema para login."""
    
    email: EmailStr = Field(
        ...,
        description="Email do usuário",
        examples=["usuario@empresa.com"],
    )
    
    password: str = Field(
        ...,
        min_length=1,
        description="Senha",
    )


# ==================== REGISTRO ====================

class RegisterRequest(BaseModel):
    """
    Schema para registro (cria tenant + user).
    
    Campos do tenant:
        - company_name: Nome da empresa
        - company_email: Email da empresa (será do tenant)
    
    Campos do usuário:
        - full_name: Nome do usuário owner
        - email: Email do usuário (pode ser diferente do tenant)
        - password: Senha
        - phone: Telefone (opcional)
    """
    
    # Dados do Tenant
    company_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nome da empresa",
        examples=["Minha Empresa LTDA"],
    )
    
    # Dados do Usuário (owner)
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nome completo do responsável",
        examples=["João Silva"],
    )
    
    email: EmailStr = Field(
        ...,
        description="Email do responsável",
        examples=["joao@empresa.com"],
    )
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Senha (mínimo 8 caracteres)",
    )
    
    phone: str | None = Field(
        None,
        max_length=20,
        description="Telefone (opcional)",
        examples=["11999998888"],
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
    
    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, v):
        if v:
            return re.sub(r"\D", "", v)
        return v


# ==================== TOKENS ====================

class TokenResponse(BaseModel):
    """Resposta com tokens JWT."""
    
    access_token: str = Field(
        ...,
        description="Token de acesso (curta duração)",
    )
    
    refresh_token: str = Field(
        ...,
        description="Token de refresh (longa duração)",
    )
    
    token_type: str = Field(
        default="bearer",
        description="Tipo do token",
    )
    
    expires_in: int = Field(
        ...,
        description="Tempo de expiração do access_token em segundos",
    )


class RefreshRequest(BaseModel):
    """Schema para refresh de token."""
    
    refresh_token: str = Field(
        ...,
        description="Refresh token válido",
    )


# ==================== RESPOSTAS COMPOSTAS ====================

class AuthResponse(BaseModel):
    """Resposta completa de auth (tokens + dados do usuário)."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    
    user: dict = Field(
        ...,
        description="Dados do usuário logado",
    )
    
    tenant: dict = Field(
        ...,
        description="Dados do tenant",
    )


class RegisterResponse(BaseModel):
    """Resposta do registro."""
    
    message: str = "Conta criada com sucesso"
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    
    user: dict
    tenant: dict


class VerifyResponse(BaseModel):
    """Resposta da verificação de token."""
    
    valid: bool = True
    user_id: str
    tenant_id: str
    role: str
    expires_at: int
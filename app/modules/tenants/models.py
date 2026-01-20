"""
Model SQLAlchemy do Tenant.

TABELA: tenants
Representa uma empresa/cliente do SaaS.

USO:
    from app.modules.tenants.models import Tenant
    
    tenant = Tenant(name="Empresa X", slug="empresa-x")
    db.add(tenant)
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.appointments.models import Appointment


class PlanType(str):
    """Tipos de plano disponíveis."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Tenant(Base):
    """
    Tenant = Empresa/Cliente do SaaS.
    
    Cada tenant tem dados isolados via tenant_id em outras tabelas.
    
    Attributes:
        id: UUID único do tenant
        name: Nome da empresa
        slug: Identificador único para URLs (ex: empresa-x)
        email: Email principal de contato
        phone: Telefone (opcional)
        document: CNPJ/CPF (opcional)
        plan: Plano de assinatura
        is_active: Se tenant está ativo
        settings: Configurações flexíveis em JSON
        n8n_instance_url: URL da instância n8n
        n8n_api_key: API key do n8n (criptografada)
    """
    
    __tablename__ = "tenants"
    
    # ==================== IDENTIFICAÇÃO ====================
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome da empresa",
    )
    
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Identificador único para URLs",
    )
    
    # ==================== CONTATO ====================
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Email principal",
    )
    
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Telefone com DDD",
    )
    
    document: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="CNPJ ou CPF",
    )
    
    # ==================== PLANO E STATUS ====================
    plan: Mapped[str] = mapped_column(
        String(50),
        default=PlanType.FREE,
        nullable=False,
        comment="Plano de assinatura",
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Tenant ativo ou suspenso",
    )
    
    # ==================== CONFIGURAÇÕES ====================
    settings: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Configurações flexíveis do tenant",
    )
    
    # ==================== INTEGRAÇÃO N8N ====================
    n8n_instance_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL da instância n8n do cliente",
    )
    
    n8n_api_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="API key do n8n (criptografada)",
    )
    
    n8n_provisioned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Se instância n8n foi provisionada",
    )
    
    # ==================== TIMESTAMPS ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # ==================== RELACIONAMENTOS ====================
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    # ==================== MÉTODOS ====================
    def __repr__(self) -> str:
        return f"<Tenant {self.slug} ({self.name})>"
    
    @property
    def is_paid(self) -> bool:
        """Retorna True se tenant tem plano pago."""
        return self.plan != PlanType.FREE
    
    def get_setting(self, key: str, default=None):
        """Obtém configuração do tenant."""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value):
        """Define configuração do tenant."""
        self.settings[key] = value
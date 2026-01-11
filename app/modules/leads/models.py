"""
Model SQLAlchemy do Lead.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    from app.modules.tenants.models import Tenant
    from app.modules.users.models import User


class LeadStatus(str, Enum):
    """Status do lead no funil."""
    NEW = "new"                    # Novo lead
    CONTACTED = "contacted"        # Já foi contatado
    QUALIFIED = "qualified"        # Qualificado (tem interesse)
    PROPOSAL = "proposal"          # Proposta enviada
    NEGOTIATION = "negotiation"    # Em negociação
    WON = "won"                    # Convertido em cliente
    LOST = "lost"                  # Perdido
    INACTIVE = "inactive"          # Inativo/arquivado


class LeadSource(str, Enum):
    """Origem do lead."""
    MANUAL = "manual"              # Cadastro manual
    WHATSAPP = "whatsapp"          # Veio pelo WhatsApp
    WEBSITE = "website"            # Formulário do site
    FACEBOOK = "facebook"          # Facebook/Instagram
    GOOGLE = "google"              # Google Ads
    REFERRAL = "referral"          # Indicação
    IMPORT = "import"              # Importação em massa
    OTHER = "other"                # Outros


class Lead(Base):
    """
    Lead/Contato do CRM.
    
    Cada lead pertence a um tenant e pode ser atribuído a um usuário.
    """
    
    __tablename__ = "leads"
    
    __table_args__ = (
        Index("ix_leads_tenant_status", "tenant_id", "status"),
        Index("ix_leads_tenant_phone", "tenant_id", "phone"),
        Index("ix_leads_tenant_email", "tenant_id", "email"),
    )
    
    # ==================== IDENTIFICAÇÃO ====================
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    # ==================== DADOS PESSOAIS ====================
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome do lead",
    )
    
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Email",
    )
    
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Telefone principal (WhatsApp)",
    )
    
    phone_secondary: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Telefone secundário",
    )
    
    document: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="CPF ou CNPJ",
    )
    
    # ==================== EMPRESA (B2B) ====================
    company_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Nome da empresa (se B2B)",
    )
    
    company_position: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Cargo na empresa",
    )
    
    # ==================== ENDEREÇO ====================
    address_street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_complement: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    address_zipcode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    
    # ==================== STATUS E ORIGEM ====================
    status: Mapped[str] = mapped_column(
        String(50),
        default=LeadStatus.NEW.value,
        nullable=False,
        index=True,
        comment="Status no funil",
    )
    
    source: Mapped[str] = mapped_column(
        String(50),
        default=LeadSource.MANUAL.value,
        nullable=False,
        comment="Origem do lead",
    )
    
    source_detail: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Detalhe da origem (ex: nome da campanha)",
    )
    
    # ==================== QUALIFICAÇÃO ====================
    score: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Score de qualificação (0-100)",
    )
    
    temperature: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Temperatura: cold, warm, hot",
    )
    
    # ==================== INTERESSE ====================
    interest: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Produto/serviço de interesse",
    )
    
    budget: Mapped[float | None] = mapped_column(
        nullable=True,
        comment="Orçamento estimado",
    )
    
    # ==================== OBSERVAÇÕES ====================
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Observações gerais",
    )
    
    # ==================== DADOS EXTRAS (JSONB) ====================
    custom_fields: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Campos personalizados",
    )
    
    tags: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Tags/etiquetas",
    )
    
    # ==================== RELACIONAMENTOS ====================
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Usuário responsável",
    )
    
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Usuário que criou",
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
    
    last_contact_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Último contato",
    )
    
    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de conversão",
    )
    
    # ==================== RELATIONSHIPS ====================
    tenant: Mapped["Tenant"] = relationship("Tenant")
    assigned_to: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_to_id],
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    
    # ==================== MÉTODOS ====================
    def __repr__(self) -> str:
        return f"<Lead {self.name} ({self.phone})>"
    
    @property
    def lead_status(self) -> LeadStatus:
        return LeadStatus(self.status)
    
    @property
    def lead_source(self) -> LeadSource:
        return LeadSource(self.source)
    
    @property
    def is_converted(self) -> bool:
        return self.status == LeadStatus.WON.value
    
    @property
    def is_active(self) -> bool:
        return self.status not in {
            LeadStatus.WON.value,
            LeadStatus.LOST.value,
            LeadStatus.INACTIVE.value,
        }
    
    def add_tag(self, tag: str):
        if tag not in self.tags:
            self.tags = [*self.tags, tag]
    
    def remove_tag(self, tag: str):
        self.tags = [t for t in self.tags if t != tag]
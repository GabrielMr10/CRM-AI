"""
Model SQLAlchemy do User.

TABELA: users
Representa um usuário do sistema.

USO:
    from app.modules.users.models import User
    
    user = User(
        email="user@empresa.com",
        hashed_password=get_password_hash("senha"),
        tenant_id=tenant.id,
    )
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.modules.users.roles import UserRole

if TYPE_CHECKING:
    from app.modules.tenants.models import Tenant


class User(Base):
    """
    Usuário do sistema.
    
    Cada usuário pertence a um tenant e tem um role.
    Email é único DENTRO do tenant (não globalmente).
    
    Attributes:
        id: UUID único
        email: Email do usuário (único por tenant)
        hashed_password: Senha hasheada (bcrypt)
        full_name: Nome completo
        phone: Telefone (opcional)
        role: Papel no sistema (owner, admin, manager, member)
        is_active: Se usuário está ativo
        is_superuser: Se é superusuário (acesso a todos tenants)
        tenant_id: FK para tenant
    """
    
    __tablename__ = "users"
    
    # Constraint: email único por tenant
    __table_args__ = (
        UniqueConstraint("email", "tenant_id", name="uq_user_email_tenant"),
    )
    
    # ==================== IDENTIFICAÇÃO ====================
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Email do usuário",
    )
    
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Senha hasheada (bcrypt)",
    )
    
    # ==================== PERFIL ====================
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome completo",
    )
    
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Telefone com DDD",
    )
    
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL do avatar",
    )
    
    # ==================== PERMISSÕES ====================
    role: Mapped[str] = mapped_column(
        String(50),
        default=UserRole.MEMBER.value,
        nullable=False,
        comment="Papel: owner, admin, manager, member",
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Usuário ativo",
    )
    
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Superusuário (acesso global)",
    )
    
    # ==================== TENANT ====================
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK para tenant",
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
    
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Último login",
    )
    
    # ==================== RELACIONAMENTOS ====================
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="users",
    )
    
    # ==================== MÉTODOS ====================
    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
    
    @property
    def user_role(self) -> UserRole:
        """Retorna role como Enum."""
        return UserRole(self.role)
    
    def has_permission(self, required_role: UserRole) -> bool:
        """Verifica se usuário tem permissão."""
        return self.user_role.has_permission(required_role)
    
    @property
    def is_owner(self) -> bool:
        """Verifica se é owner do tenant."""
        return self.role == UserRole.OWNER.value
    
    @property
    def is_admin(self) -> bool:
        """Verifica se é admin ou owner."""
        return self.role in {UserRole.OWNER.value, UserRole.ADMIN.value}
    
    @property
    def can_manage_users(self) -> bool:
        """Verifica se pode gerenciar usuários."""
        return self.is_admin
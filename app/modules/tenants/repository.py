"""
Repository - Queries isoladas do banco de dados.
Não contém lógica de negócio, apenas CRUD.

USO:
    from app.modules.tenants.repository import TenantRepository
    
    tenant = TenantRepository.get_by_slug(db, "minha-empresa")
    tenants = TenantRepository.get_all(db, skip=0, limit=10)
"""
import uuid
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.modules.tenants.models import Tenant
from app.modules.tenants.schemas import TenantCreate, TenantUpdate


class TenantRepository:
    """
    Repositório de Tenants.
    Métodos estáticos para queries no banco.
    """
    
    # ==================== READ ====================
    
    @staticmethod
    def get_by_id(db: Session, tenant_id: uuid.UUID) -> Tenant | None:
        """Busca tenant por ID."""
        return db.get(Tenant, tenant_id)
    
    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Tenant | None:
        """Busca tenant por slug."""
        stmt = select(Tenant).where(Tenant.slug == slug)
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> Tenant | None:
        """Busca tenant por email."""
        stmt = select(Tenant).where(Tenant.email == email)
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_all(
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> Sequence[Tenant]:
        """
        Lista tenants com paginação.
        
        Args:
            skip: Offset para paginação
            limit: Limite de registros
            is_active: Filtro por status (opcional)
        """
        stmt = select(Tenant).offset(skip).limit(limit).order_by(Tenant.created_at.desc())
        
        if is_active is not None:
            stmt = stmt.where(Tenant.is_active == is_active)
        
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def count(db: Session, *, is_active: bool | None = None) -> int:
        """Conta total de tenants."""
        stmt = select(func.count(Tenant.id))
        
        if is_active is not None:
            stmt = stmt.where(Tenant.is_active == is_active)
        
        return db.execute(stmt).scalar_one()
    
    @staticmethod
    def exists_slug(db: Session, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
        """Verifica se slug já existe."""
        stmt = select(Tenant.id).where(Tenant.slug == slug)
        
        if exclude_id:
            stmt = stmt.where(Tenant.id != exclude_id)
        
        return db.execute(stmt).scalar_one_or_none() is not None
    
    @staticmethod
    def exists_email(db: Session, email: str, exclude_id: uuid.UUID | None = None) -> bool:
        """Verifica se email já existe."""
        stmt = select(Tenant.id).where(Tenant.email == email)
        
        if exclude_id:
            stmt = stmt.where(Tenant.id != exclude_id)
        
        return db.execute(stmt).scalar_one_or_none() is not None
    
    # ==================== CREATE ====================
    
    @staticmethod
    def create(db: Session, *, data: TenantCreate) -> Tenant:
        """
        Cria novo tenant.
        
        Args:
            data: Dados validados do schema
        
        Returns:
            Tenant criado
        """
        tenant = Tenant(
            name=data.name,
            slug=data.slug,
            email=data.email,
            phone=data.phone,
            document=data.document,
        )
        
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        
        return tenant
    
    # ==================== UPDATE ====================
    
    @staticmethod
    def update(db: Session, *, tenant: Tenant, data: TenantUpdate) -> Tenant:
        """
        Atualiza tenant existente.
        
        Args:
            tenant: Objeto tenant do banco
            data: Dados para atualizar (campos None são ignorados)
        
        Returns:
            Tenant atualizado
        """
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(tenant, field, value)
        
        db.commit()
        db.refresh(tenant)
        
        return tenant
    
    @staticmethod
    def update_n8n_config(
        db: Session,
        *,
        tenant: Tenant,
        instance_url: str,
        api_key: str,
    ) -> Tenant:
        """Atualiza configuração do n8n."""
        tenant.n8n_instance_url = instance_url
        tenant.n8n_api_key = api_key
        tenant.n8n_provisioned = True
        
        db.commit()
        db.refresh(tenant)
        
        return tenant
    
    # ==================== DELETE ====================
    
    @staticmethod
    def delete(db: Session, *, tenant: Tenant) -> None:
        """Remove tenant (cascade deleta users, leads, etc)."""
        db.delete(tenant)
        db.commit()
    
    @staticmethod
    def deactivate(db: Session, *, tenant: Tenant) -> Tenant:
        """Desativa tenant (soft delete)."""
        tenant.is_active = False
        db.commit()
        db.refresh(tenant)
        return tenant
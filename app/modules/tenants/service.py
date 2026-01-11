"""
Service - Lógica de negócio do módulo Tenants.
Orquestra repository, validações e regras.

USO:
    from app.modules.tenants.service import TenantService
    
    tenant = TenantService.create(db, data=tenant_data)
    tenant = TenantService.get_or_404(db, tenant_id)
"""
import uuid
from math import ceil

from sqlalchemy.orm import Session

from app.modules.tenants.models import Tenant
from app.modules.tenants.schemas import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
)
from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.exceptions import (
    TenantNotFoundError,
    TenantSlugExistsError,
    TenantEmailExistsError,
    TenantInactiveError,
)


class TenantService:
    """
    Serviço de Tenants.
    Contém regras de negócio e validações.
    """
    
    # ==================== READ ====================
    
    @staticmethod
    def get_or_404(db: Session, tenant_id: uuid.UUID) -> Tenant:
        """
        Busca tenant por ID ou lança 404.
        
        Raises:
            TenantNotFoundError: Se não encontrado
        """
        tenant = TenantRepository.get_by_id(db, tenant_id)
        
        if not tenant:
            raise TenantNotFoundError(str(tenant_id))
        
        return tenant
    
    @staticmethod
    def get_by_slug_or_404(db: Session, slug: str) -> Tenant:
        """
        Busca tenant por slug ou lança 404.
        
        Raises:
            TenantNotFoundError: Se não encontrado
        """
        tenant = TenantRepository.get_by_slug(db, slug)
        
        if not tenant:
            raise TenantNotFoundError(slug)
        
        return tenant
    
    @staticmethod
    def get_active_or_403(db: Session, tenant_id: uuid.UUID) -> Tenant:
        """
        Busca tenant ativo ou lança erro.
        
        Raises:
            TenantNotFoundError: Se não encontrado
            TenantInactiveError: Se tenant inativo
        """
        tenant = TenantService.get_or_404(db, tenant_id)
        
        if not tenant.is_active:
            raise TenantInactiveError()
        
        return tenant
    
    @staticmethod
    def list_paginated(
        db: Session,
        *,
        page: int = 1,
        per_page: int = 20,
        is_active: bool | None = None,
    ) -> TenantListResponse:
        """
        Lista tenants com paginação.
        
        Args:
            page: Número da página (1-indexed)
            per_page: Itens por página
            is_active: Filtro opcional por status
        
        Returns:
            TenantListResponse com items e metadados
        """
        skip = (page - 1) * per_page
        
        tenants = TenantRepository.get_all(
            db,
            skip=skip,
            limit=per_page,
            is_active=is_active,
        )
        
        total = TenantRepository.count(db, is_active=is_active)
        pages = ceil(total / per_page) if total > 0 else 1
        
        return TenantListResponse(
            items=[TenantResponse.model_validate(t) for t in tenants],
            total=total,
            page=page,
            pages=pages,
            per_page=per_page,
        )
    
    # ==================== CREATE ====================
    
    @staticmethod
    def create(db: Session, *, data: TenantCreate) -> Tenant:
        """
        Cria novo tenant com validações.
        
        Validações:
            - Slug único
            - Email único
        
        Raises:
            TenantSlugExistsError: Se slug já existe
            TenantEmailExistsError: Se email já existe
        
        Returns:
            Tenant criado
        """
        # Validar slug único
        if TenantRepository.exists_slug(db, data.slug):
            raise TenantSlugExistsError(data.slug)
        
        # Validar email único
        if TenantRepository.exists_email(db, data.email):
            raise TenantEmailExistsError(data.email)
        
        # Criar tenant
        tenant = TenantRepository.create(db, data=data)
        
        return tenant
    
    # ==================== UPDATE ====================
    
    @staticmethod
    def update(
        db: Session,
        *,
        tenant_id: uuid.UUID,
        data: TenantUpdate,
    ) -> Tenant:
        """
        Atualiza tenant existente.
        
        Raises:
            TenantNotFoundError: Se não encontrado
            TenantEmailExistsError: Se novo email já existe
        
        Returns:
            Tenant atualizado
        """
        tenant = TenantService.get_or_404(db, tenant_id)
        
        # Validar email único se estiver alterando
        if data.email and data.email != tenant.email:
            if TenantRepository.exists_email(db, data.email, exclude_id=tenant_id):
                raise TenantEmailExistsError(data.email)
        
        return TenantRepository.update(db, tenant=tenant, data=data)
    
    # ==================== DELETE ====================
    
    @staticmethod
    def delete(db: Session, *, tenant_id: uuid.UUID) -> None:
        """
        Remove tenant permanentemente.
        
        CUIDADO: Isso remove TODOS os dados do tenant (cascade).
        
        Raises:
            TenantNotFoundError: Se não encontrado
        """
        tenant = TenantService.get_or_404(db, tenant_id)
        TenantRepository.delete(db, tenant=tenant)
    
    @staticmethod
    def deactivate(db: Session, *, tenant_id: uuid.UUID) -> Tenant:
        """
        Desativa tenant (soft delete).
        Dados são mantidos mas tenant não pode operar.
        
        Raises:
            TenantNotFoundError: Se não encontrado
        """
        tenant = TenantService.get_or_404(db, tenant_id)
        return TenantRepository.deactivate(db, tenant=tenant)
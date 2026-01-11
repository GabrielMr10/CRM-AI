"""
Router - Endpoints HTTP do módulo Users.

Prefixo: /api/v1/users
Tags: ["Users"]
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.modules.users.models import User
from app.modules.users.roles import UserRole
from app.modules.users.schemas import (
    UserCreate,
    UserUpdate,
    UserUpdateByAdmin,
    UserChangePassword,
    UserResponse,
    UserListResponse,
)
from app.modules.users.service import UserService
from app.modules.users.exceptions import InsufficientPermissionError
from app.modules.tenants.dependencies import get_current_tenant, CurrentTenant

router = APIRouter()


# ==================== DEPENDENCY HELPERS ====================

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Exige que usuário seja admin ou owner."""
    if not current_user.can_manage_users:
        raise InsufficientPermissionError("gerenciar usuários")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


# ==================== PRÓPRIO USUÁRIO ====================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Meus dados",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """Retorna dados do usuário logado."""
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Atualizar meu perfil",
)
def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Atualiza perfil do usuário logado."""
    return UserService.update_self(db, user=current_user, data=data)


@router.post(
    "/me/change-password",
    response_model=UserResponse,
    summary="Trocar minha senha",
)
def change_my_password(
    data: UserChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Troca senha do usuário logado."""
    return UserService.change_password(db, user=current_user, data=data)


# ==================== ADMIN - GERENCIAR USUÁRIOS ====================

@router.get(
    "/",
    response_model=UserListResponse,
    summary="Listar usuários",
    description="Lista usuários do tenant. Requer permissão de admin.",
)
def list_users(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(),
    tenant: CurrentTenant = Depends(),
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    is_active: Annotated[bool | None, Query()] = None,
):
    """Lista usuários do tenant."""
    return UserService.list_by_tenant_paginated(
        db,
        tenant.id,
        page=page,
        per_page=per_page,
        is_active=is_active,
    )


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar usuário",
)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(),
    tenant: CurrentTenant = Depends(),
):
    """Cria novo usuário no tenant."""
    return UserService.create(
        db,
        data=data,
        tenant_id=tenant.id,
        created_by=admin,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Detalhe do usuário",
)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(),
    tenant: CurrentTenant = Depends(),
):
    """Retorna detalhes de um usuário."""
    user = UserService.get_or_404(db, user_id)
    
    # Garantir que é do mesmo tenant
    if user.tenant_id != tenant.id:
        raise InsufficientPermissionError("acessar este usuário")
    
    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Atualizar usuário",
)
def update_user(
    user_id: uuid.UUID,
    data: UserUpdateByAdmin,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(),
    tenant: CurrentTenant = Depends(),
):
    """Atualiza dados de um usuário."""
    user = UserService.get_or_404(db, user_id)
    
    if user.tenant_id != tenant.id:
        raise InsufficientPermissionError("acessar este usuário")
    
    return UserService.update_by_admin(
        db,
        user_id=user_id,
        data=data,
        admin=admin,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover usuário",
)
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(),
    tenant: CurrentTenant = Depends(),
):
    """Remove usuário do tenant."""
    user = UserService.get_or_404(db, user_id)
    
    if user.tenant_id != tenant.id:
        raise InsufficientPermissionError("acessar este usuário")
    
    UserService.delete(db, user_id=user_id, deleted_by=admin)
    return None


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Desativar usuário",
)
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(),
    tenant: CurrentTenant = Depends(),
):
    """Desativa usuário (soft delete)."""
    user = UserService.get_or_404(db, user_id)
    
    if user.tenant_id != tenant.id:
        raise InsufficientPermissionError("acessar este usuário")
    
    return UserService.deactivate(db, user_id=user_id, deactivated_by=admin)


@router.post(
    "/{user_id}/activate",
    response_model=UserResponse,
    summary="Reativar usuário",
)
def activate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(),
    tenant: CurrentTenant = Depends(),
):
    """Reativa usuário desativado."""
    user = UserService.get_or_404(db, user_id)
    
    if user.tenant_id != tenant.id:
        raise InsufficientPermissionError("acessar este usuário")
    
    return UserService.update_by_admin(
        db,
        user_id=user_id,
        data=UserUpdateByAdmin(is_active=True),
        admin=admin,
    )
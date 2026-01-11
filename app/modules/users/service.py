"""
Service - Lógica de negócio do módulo Users.
"""
import uuid
from math import ceil

from sqlalchemy.orm import Session

from app.core.security import verify_password
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
from app.modules.users.repository import UserRepository
from app.modules.users.exceptions import (
    UserNotFoundError,
    UserEmailExistsError,
    UserInactiveError,
    CannotDeleteOwnerError,
    CannotChangeOwnRoleError,
    InvalidPasswordError,
    InsufficientPermissionError,
)


class UserService:
    """Serviço de Users."""
    
    # ==================== READ ====================
    
    @staticmethod
    def get_or_404(db: Session, user_id: uuid.UUID) -> User:
        """Busca usuário ou lança 404."""
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise UserNotFoundError(str(user_id))
        return user
    
    @staticmethod
    def get_by_email_or_404(
        db: Session,
        email: str,
        tenant_id: uuid.UUID,
    ) -> User:
        """Busca por email no tenant ou lança 404."""
        user = UserRepository.get_by_email(db, email, tenant_id)
        if not user:
            raise UserNotFoundError(email)
        return user
    
    @staticmethod
    def get_active_or_403(db: Session, user_id: uuid.UUID) -> User:
        """Busca usuário ativo ou lança erro."""
        user = UserService.get_or_404(db, user_id)
        if not user.is_active:
            raise UserInactiveError()
        return user
    
    @staticmethod
    def list_by_tenant_paginated(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
        is_active: bool | None = None,
    ) -> UserListResponse:
        """Lista usuários do tenant com paginação."""
        skip = (page - 1) * per_page
        
        users = UserRepository.get_all_by_tenant(
            db,
            tenant_id,
            skip=skip,
            limit=per_page,
            is_active=is_active,
        )
        
        total = UserRepository.count_by_tenant(db, tenant_id, is_active=is_active)
        pages = ceil(total / per_page) if total > 0 else 1
        
        return UserListResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            pages=pages,
            per_page=per_page,
        )
    
    # ==================== CREATE ====================
    
    @staticmethod
    def create(
        db: Session,
        *,
        data: UserCreate,
        tenant_id: uuid.UUID,
        created_by: User | None = None,
    ) -> User:
        """
        Cria usuário no tenant.
        
        Validações:
            - Email único no tenant
            - Se created_by informado, verifica permissão
        """
        # Validar email único
        if UserRepository.exists_email_in_tenant(db, data.email, tenant_id):
            raise UserEmailExistsError(data.email)
        
        # Verificar permissão para criar com role específico
        if created_by and data.role != UserRole.MEMBER:
            if not created_by.has_permission(UserRole.ADMIN):
                raise InsufficientPermissionError("criar usuário com este papel")
        
        return UserRepository.create(
            db,
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            tenant_id=tenant_id,
            role=data.role.value if isinstance(data.role, UserRole) else data.role,
            phone=data.phone,
        )
    
    @staticmethod
    def create_owner(
        db: Session,
        *,
        email: str,
        password: str,
        full_name: str,
        tenant_id: uuid.UUID,
    ) -> User:
        """Cria owner do tenant (usado no signup)."""
        return UserRepository.create(
            db,
            email=email,
            password=password,
            full_name=full_name,
            tenant_id=tenant_id,
            role=UserRole.OWNER.value,
        )
    
    # ==================== UPDATE ====================
    
    @staticmethod
    def update_self(
        db: Session,
        *,
        user: User,
        data: UserUpdate,
    ) -> User:
        """Usuário atualiza próprio perfil."""
        return UserRepository.update(db, user=user, data=data)
    
    @staticmethod
    def update_by_admin(
        db: Session,
        *,
        user_id: uuid.UUID,
        data: UserUpdateByAdmin,
        admin: User,
    ) -> User:
        """
        Admin atualiza outro usuário.
        
        Validações:
            - Não pode alterar próprio role
            - Não pode alterar owner
            - Email único se alterado
        """
        user = UserService.get_or_404(db, user_id)
        
        # Não pode alterar próprio role
        if user.id == admin.id and data.role is not None:
            raise CannotChangeOwnRoleError()
        
        # Não pode alterar owner (exceto se for o próprio owner)
        if user.is_owner and user.id != admin.id:
            raise InsufficientPermissionError("alterar o proprietário")
        
        # Validar email único se alterado
        if data.email and data.email != user.email:
            if UserRepository.exists_email_in_tenant(
                db, data.email, user.tenant_id, exclude_id=user.id
            ):
                raise UserEmailExistsError(data.email)
        
        return UserRepository.update(db, user=user, data=data)
    
    @staticmethod
    def change_password(
        db: Session,
        *,
        user: User,
        data: UserChangePassword,
    ) -> User:
        """Usuário troca própria senha."""
        if not verify_password(data.current_password, user.hashed_password):
            raise InvalidPasswordError()
        
        return UserRepository.update_password(db, user=user, new_password=data.new_password)
    
    # ==================== DELETE ====================
    
    @staticmethod
    def delete(
        db: Session,
        *,
        user_id: uuid.UUID,
        deleted_by: User,
    ) -> None:
        """
        Remove usuário.
        
        Validações:
            - Não pode deletar owner
            - Não pode deletar a si mesmo
        """
        user = UserService.get_or_404(db, user_id)
        
        if user.is_owner:
            raise CannotDeleteOwnerError()
        
        if user.id == deleted_by.id:
            raise InsufficientPermissionError("remover a si mesmo")
        
        UserRepository.delete(db, user=user)
    
    @staticmethod
    def deactivate(
        db: Session,
        *,
        user_id: uuid.UUID,
        deactivated_by: User,
    ) -> User:
        """Desativa usuário (soft delete)."""
        user = UserService.get_or_404(db, user_id)
        
        if user.is_owner:
            raise CannotDeleteOwnerError()
        
        return UserRepository.deactivate(db, user=user)
"""
Repository - Queries isoladas do banco de dados.
"""
import uuid
from typing import Sequence
from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate, UserUpdateByAdmin
from app.core.security import get_password_hash


class UserRepository:
    """Repositório de Users."""
    
    # ==================== READ ====================
    
    @staticmethod
    def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
        """Busca usuário por ID."""
        return db.get(User, user_id)
    
    @staticmethod
    def get_by_email(db: Session, email: str, tenant_id: uuid.UUID) -> User | None:
        """Busca usuário por email dentro do tenant."""
        stmt = select(User).where(
            and_(
                User.email == email,
                User.tenant_id == tenant_id,
            )
        )
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_by_email_global(db: Session, email: str) -> User | None:
        """
        Busca usuário por email em qualquer tenant.
        Usado apenas para login (antes de saber o tenant).
        """
        stmt = select(User).where(User.email == email)
        return db.execute(stmt).scalar_one_or_none()
    
    @staticmethod
    def get_all_by_tenant(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> Sequence[User]:
        """Lista usuários do tenant."""
        stmt = (
            select(User)
            .where(User.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def count_by_tenant(
        db: Session,
        tenant_id: uuid.UUID,
        *,
        is_active: bool | None = None,
    ) -> int:
        """Conta usuários do tenant."""
        stmt = select(func.count(User.id)).where(User.tenant_id == tenant_id)
        
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        
        return db.execute(stmt).scalar_one()
    
    @staticmethod
    def exists_email_in_tenant(
        db: Session,
        email: str,
        tenant_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """Verifica se email já existe no tenant."""
        stmt = select(User.id).where(
            and_(
                User.email == email,
                User.tenant_id == tenant_id,
            )
        )
        
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)
        
        return db.execute(stmt).scalar_one_or_none() is not None
    
    # ==================== CREATE ====================
    
    @staticmethod
    def create(
        db: Session,
        *,
        email: str,
        password: str,
        full_name: str,
        tenant_id: uuid.UUID,
        role: str = "member",
        phone: str | None = None,
        is_superuser: bool = False,
    ) -> User:
        """Cria novo usuário."""
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            tenant_id=tenant_id,
            role=role,
            phone=phone,
            is_superuser=is_superuser,
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    # ==================== UPDATE ====================
    
    @staticmethod
    def update(
        db: Session,
        *,
        user: User,
        data: UserUpdate | UserUpdateByAdmin,
    ) -> User:
        """Atualiza usuário."""
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def update_password(db: Session, *, user: User, new_password: str) -> User:
        """Atualiza senha do usuário."""
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_last_login(db: Session, *, user: User) -> User:
        """Atualiza timestamp do último login."""
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user
    
    # ==================== DELETE ====================
    
    @staticmethod
    def delete(db: Session, *, user: User) -> None:
        """Remove usuário."""
        db.delete(user)
        db.commit()
    
    @staticmethod
    def deactivate(db: Session, *, user: User) -> User:
        """Desativa usuário."""
        user.is_active = False
        db.commit()
        db.refresh(user)
        return user
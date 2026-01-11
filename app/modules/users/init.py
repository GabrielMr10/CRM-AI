"""
Users Module
Gerencia usuários do sistema com roles.
"""
from app.modules.users.models import User
from app.modules.users.roles import UserRole
from app.modules.users.schemas import UserCreate, UserUpdate, UserResponse
from app.modules.users.service import UserService

__all__ = [
    "User",
    "UserRole",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserService",
]
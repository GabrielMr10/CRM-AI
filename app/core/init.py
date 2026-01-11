"""
Core Module - Fundação do sistema
Exporta configurações, segurança e dependências globais.
"""
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
)
from app.core.exceptions import (
    BadRequestException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    ConflictException,
)

__all__ = [
    "settings",
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "create_refresh_token",
    "BadRequestException",
    "UnauthorizedException",
    "ForbiddenException",
    "NotFoundException",
    "ConflictException",
]
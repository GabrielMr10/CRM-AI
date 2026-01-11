"""
Exceções específicas do módulo Auth.
"""
from app.core.exceptions import (
    UnauthorizedException,
    BadRequestException,
)


class InvalidCredentialsError(UnauthorizedException):
    """Credenciais inválidas (email ou senha incorretos)."""
    
    def __init__(self):
        super().__init__(detail="Email ou senha incorretos")


class InvalidTokenError(UnauthorizedException):
    """Token inválido ou expirado."""
    
    def __init__(self, message: str = "Token inválido ou expirado"):
        super().__init__(detail=message)


class InvalidRefreshTokenError(UnauthorizedException):
    """Refresh token inválido."""
    
    def __init__(self):
        super().__init__(detail="Refresh token inválido ou expirado")


class AccountDisabledError(UnauthorizedException):
    """Conta desativada."""
    
    def __init__(self):
        super().__init__(detail="Sua conta está desativada. Entre em contato com o suporte.")


class TenantSuspendedError(UnauthorizedException):
    """Tenant suspenso."""
    
    def __init__(self):
        super().__init__(detail="Sua empresa está suspensa. Entre em contato com o suporte.")


class EmailAlreadyRegisteredError(BadRequestException):
    """Email já cadastrado."""
    
    def __init__(self, email: str):
        super().__init__(detail=f"Email '{email}' já está cadastrado")
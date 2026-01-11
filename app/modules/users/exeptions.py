"""
Exceções específicas do módulo Users.
"""
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    ForbiddenException,
    BadRequestException,
)


class UserNotFoundError(NotFoundException):
    """Usuário não encontrado."""
    
    def __init__(self, user_id: str | None = None):
        detail = "Usuário não encontrado"
        if user_id:
            detail = f"Usuário '{user_id}' não encontrado"
        super().__init__(detail=detail)


class UserEmailExistsError(ConflictException):
    """Email já cadastrado neste tenant."""
    
    def __init__(self, email: str):
        super().__init__(detail=f"Email '{email}' já está cadastrado")


class UserInactiveError(ForbiddenException):
    """Usuário inativo."""
    
    def __init__(self):
        super().__init__(detail="Usuário desativado")


class CannotDeleteOwnerError(ForbiddenException):
    """Não pode deletar owner do tenant."""
    
    def __init__(self):
        super().__init__(detail="Não é possível remover o proprietário do tenant")


class CannotChangeOwnRoleError(ForbiddenException):
    """Não pode alterar próprio role."""
    
    def __init__(self):
        super().__init__(detail="Não é possível alterar seu próprio papel")


class InvalidPasswordError(BadRequestException):
    """Senha atual incorreta."""
    
    def __init__(self):
        super().__init__(detail="Senha atual incorreta")


class InsufficientPermissionError(ForbiddenException):
    """Permissão insuficiente."""
    
    def __init__(self, action: str = "realizar esta ação"):
        super().__init__(detail=f"Você não tem permissão para {action}")
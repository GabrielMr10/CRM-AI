"""
Exceções HTTP customizadas para uso em toda a aplicação.
Padroniza mensagens de erro e códigos de status.

USO:
    from app.core.exceptions import NotFoundException
    
    if not user:
        raise NotFoundException("Usuário não encontrado")

NOTA: Essas exceções são HTTPException do FastAPI,
então são automaticamente convertidas em respostas HTTP.
"""
from fastapi import HTTPException, status


class BadRequestException(HTTPException):
    """
    400 - Requisição inválida.
    Use quando: dados de entrada inválidos, validação falhou.
    """
    def __init__(self, detail: str = "Requisição inválida"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(HTTPException):
    """
    401 - Não autenticado.
    Use quando: token ausente, inválido ou expirado.
    """
    def __init__(self, detail: str = "Não autenticado"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(HTTPException):
    """
    403 - Acesso negado.
    Use quando: usuário autenticado mas sem permissão.
    """
    def __init__(self, detail: str = "Acesso negado"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundException(HTTPException):
    """
    404 - Recurso não encontrado.
    Use quando: ID não existe no banco.
    """
    def __init__(self, detail: str = "Recurso não encontrado"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictException(HTTPException):
    """
    409 - Conflito.
    Use quando: email já cadastrado, slug duplicado, etc.
    """
    def __init__(self, detail: str = "Conflito com recurso existente"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnprocessableEntityException(HTTPException):
    """
    422 - Entidade não processável.
    Use quando: dados válidos mas regra de negócio impede ação.
    """
    def __init__(self, detail: str = "Não foi possível processar a requisição"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class InternalServerException(HTTPException):
    """
    500 - Erro interno.
    Use quando: erro inesperado no servidor.
    """
    def __init__(self, detail: str = "Erro interno do servidor"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )
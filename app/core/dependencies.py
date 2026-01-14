"""
Dependências de injeção do FastAPI.
Use em rotas com Depends().

USO:
    from app.core.dependencies import get_db, get_current_user

    @router.get("/users")
    def list_users(db: Session = Depends(get_db)):
        ...

    @router.get("/me")
    def get_me(current_user: User = Depends(get_current_user)):
        ...
"""
import uuid
from typing import Generator, Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException, NotFoundException
from app.db.session import SessionLocal

# OAuth2 scheme - extrai token do header "Authorization: Bearer <token>"
# Usa /login/form para compatibilidade com Swagger UI (OAuth2PasswordRequestForm)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login/form")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency que fornece sessão do banco.
    Fecha automaticamente após a requisição.

    USO:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """
    Dependency que extrai e valida usuário do token JWT.

    Retorna o objeto User do banco de dados.

    Raises:
        UnauthorizedException: Se token inválido
        NotFoundException: Se usuário não existe mais

    NOTA: Importamos User aqui dentro para evitar import circular.
    """
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None:
            raise UnauthorizedException("Token inválido")

        if token_type != "access":
            raise UnauthorizedException("Tipo de token inválido")

    except JWTError:
        raise UnauthorizedException("Token inválido ou expirado")

    # Import tardio para evitar circular import
    from app.modules.users.repository import UserRepository

    user = UserRepository.get_by_id(db, uuid.UUID(user_id))

    if user is None:
        raise NotFoundException("Usuário não encontrado")

    if not user.is_active:
        raise UnauthorizedException("Usuário desativado")

    return user


async def get_current_active_superuser(
    current_user = Depends(get_current_user),
):
    """
    Dependency que exige superusuário.

    USO:
        @router.delete("/tenants/{id}")
        def delete_tenant(user = Depends(get_current_active_superuser)):
            ...
    """
    if not current_user.is_superuser:
        raise UnauthorizedException("Acesso restrito a administradores")
    return current_user


# Type aliases para uso mais limpo nas rotas
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[any, Depends(get_current_user)]  # Será tipado como User depois
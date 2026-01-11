"""
Funções de segurança: hash de senha e JWT.

USO:
    from app.core.security import verify_password, create_access_token
    
    hashed = get_password_hash("minha_senha")
    is_valid = verify_password("minha_senha", hashed)
    token = create_access_token({"sub": "user@email.com", "tenant_id": "uuid"})
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

# Contexto de hash - bcrypt é o padrão seguro atual
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==================== SENHA ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha em texto puro corresponde ao hash.
    
    Args:
        plain_password: Senha digitada pelo usuário
        hashed_password: Hash armazenado no banco
    
    Returns:
        True se senha correta, False caso contrário
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Gera hash bcrypt da senha.
    
    Args:
        password: Senha em texto puro
    
    Returns:
        Hash bcrypt (60 caracteres)
    """
    return pwd_context.hash(password)


# ==================== JWT ====================

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Cria token JWT de acesso.
    
    Args:
        data: Payload do token (deve conter "sub" com ID/email do usuário)
        expires_delta: Tempo de expiração customizado (opcional)
    
    Returns:
        Token JWT codificado
    
    Exemplo de payload:
        {
            "sub": "user_id_ou_email",
            "tenant_id": "uuid_do_tenant",
            "role": "admin"
        }
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "type": "access"
    })
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Cria token JWT de refresh (renovação).
    Expira em REFRESH_TOKEN_EXPIRE_DAYS dias.
    
    Args:
        data: Payload mínimo (geralmente só "sub")
    
    Returns:
        Token JWT de refresh
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decodifica e valida token JWT.
    
    Args:
        token: Token JWT
    
    Returns:
        Payload decodificado
    
    Raises:
        jose.JWTError: Se token inválido ou expirado
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
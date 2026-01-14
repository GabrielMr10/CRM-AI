"""
Router - Endpoints de autenticação.

Prefixo: /api/v1/auth
Tags: ["Auth"]
"""
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user, oauth2_scheme
from app.modules.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    AuthResponse,
    RegisterResponse,
    RefreshRequest,
    VerifyResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter()


# ==================== PÚBLICO ====================

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nova conta",
    description="Cria um novo tenant (empresa) e usuário administrador.",
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Registra nova conta.
    
    Cria:
    - **Tenant**: Empresa com os dados informados
    - **User**: Usuário owner (administrador) da empresa
    
    Retorna tokens JWT para login automático.
    """
    return AuthService.register(db, data=data)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login",
    description="Autentica usuário e retorna tokens JWT.",
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Autentica usuário.
    
    Retorna:
    - **access_token**: Token de curta duração para requisições
    - **refresh_token**: Token de longa duração para renovar access_token
    - **user**: Dados do usuário logado
    - **tenant**: Dados da empresa
    """
    return AuthService.login(db, data=data)


@router.post(
    "/login/form",
    response_model=AuthResponse,
    summary="Login (OAuth2 Form)",
    description="Login compatível com OAuth2 form (usado pelo botão Authorize do Swagger UI).",
    include_in_schema=True,  # Visível para Swagger UI usar no Authorize
)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login via form (para Swagger UI)."""
    data = LoginRequest(email=form_data.username, password=form_data.password)
    return AuthService.login(db, data=data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar token",
    description="Renova access_token usando refresh_token.",
)
def refresh_token(
    data: RefreshRequest,
    db: Session = Depends(get_db),
):
    """
    Renova access_token.
    
    Envie o refresh_token para obter um novo access_token.
    O refresh_token continua válido até expirar.
    """
    return AuthService.refresh_token(db, refresh_token=data.refresh_token)


# ==================== AUTENTICADO ====================

@router.get(
    "/verify",
    response_model=VerifyResponse,
    summary="Verificar token",
    description="Verifica se o token atual é válido.",
)
def verify_token(
    token: str = Depends(oauth2_scheme),
):
    """
    Verifica validade do token.
    
    Útil para verificar se o usuário ainda está autenticado
    sem fazer uma requisição completa.
    """
    return AuthService.verify_token(token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Encerra sessão (client-side).",
)
def logout(
    current_user = Depends(get_current_user),
):
    """
    Logout.
    
    Nota: JWT é stateless, então o logout é feito client-side
    removendo os tokens do storage.
    
    Em implementações futuras, pode-se adicionar blacklist de tokens.
    """
    # Em produção, você pode:
    # 1. Adicionar refresh_token a uma blacklist no Redis
    # 2. Invalidar todas as sessões do usuário
    # Por ora, apenas retorna sucesso
    return None
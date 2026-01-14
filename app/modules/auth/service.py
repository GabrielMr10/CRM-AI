"""
Service - Lógica de autenticação.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from jose import JWTError

from app.core.config import settings
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.modules.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    AuthResponse,
    RegisterResponse,
    VerifyResponse,
)
from app.modules.auth.exceptions import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    AccountDisabledError,
    TenantSuspendedError,
    EmailAlreadyRegisteredError,
)
from app.modules.tenants.models import Tenant
from app.modules.tenants.schemas import TenantCreate, TenantResponse
from app.modules.tenants.repository import TenantRepository
from app.modules.users.models import User
from app.modules.users.schemas import UserResponse
from app.modules.users.repository import UserRepository
from app.modules.users.roles import UserRole


class AuthService:
    """Serviço de autenticação."""
    
    # ==================== LOGIN ====================
    
    @staticmethod
    def login(db: Session, *, data: LoginRequest) -> AuthResponse:
        """
        Autentica usuário e retorna tokens.
        
        Fluxo:
            1. Busca usuário por email (global)
            2. Valida senha
            3. Verifica se usuário está ativo
            4. Verifica se tenant está ativo
            5. Atualiza last_login
            6. Gera tokens
        
        Raises:
            InvalidCredentialsError: Email ou senha incorretos
            AccountDisabledError: Usuário desativado
            TenantSuspendedError: Tenant suspenso
        """
        # 1. Buscar usuário por email
        user = UserRepository.get_by_email_global(db, data.email)
        
        if not user:
            raise InvalidCredentialsError()
        
        # 2. Validar senha
        if not verify_password(data.password, user.hashed_password):
            raise InvalidCredentialsError()
        
        # 3. Verificar se usuário está ativo
        if not user.is_active:
            raise AccountDisabledError()
        
        # 4. Verificar se tenant está ativo
        tenant = TenantRepository.get_by_id(db, user.tenant_id)
        
        if not tenant or not tenant.is_active:
            raise TenantSuspendedError()
        
        # 5. Atualizar last_login
        UserRepository.update_last_login(db, user=user)
        
        # 6. Gerar tokens
        tokens = AuthService._generate_tokens(user)
        
        return AuthResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user).model_dump(),
            tenant=TenantResponse.model_validate(tenant).model_dump(),
        )
    
    # ==================== REGISTRO ====================
    
    @staticmethod
    def register(db: Session, *, data: RegisterRequest) -> RegisterResponse:
        """
        Registra novo tenant + usuário owner.
        
        Fluxo:
            1. Valida email único (global, pois owner é único)
            2. Cria tenant
            3. Cria user owner
            4. Gera tokens
        
        Raises:
            EmailAlreadyRegisteredError: Email já existe
            TenantSlugExistsError: Slug já existe (improvável)
        """
        # 1. Validar email único globalmente
        existing_user = UserRepository.get_by_email_global(db, data.email)

        if existing_user:
            raise EmailAlreadyRegisteredError(data.email)

        # 2. Criar tenant com slug gerado automaticamente pelo validator
        # NÃO passar slug=None - deixa o validator do schema gerar
        tenant_data = TenantCreate(
            name=data.company_name,
            email=data.email,
            phone=data.phone if hasattr(data, 'phone') else None,
            document=data.document if hasattr(data, 'document') else None,
            # slug será gerado automaticamente pelo model_validator
        )

        # 3. Verificar se slug existe e garantir unicidade
        base_slug = tenant_data.slug
        final_slug = base_slug
        counter = 0

        while TenantRepository.exists_slug(db, final_slug):
            counter += 1
            if counter == 1:
                final_slug = f"{base_slug}-{str(uuid.uuid4())[:6]}"
            else:
                final_slug = f"{base_slug}-{counter}"

        # Atualizar slug garantido como único
        tenant_data.slug = final_slug

        # 4. Criar tenant no banco
        tenant = TenantRepository.create(db, data=tenant_data)

        # 5. Criar user owner
        user = UserRepository.create(
            db,
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            tenant_id=tenant.id,
            role=UserRole.OWNER.value,
            phone=data.phone if hasattr(data, 'phone') else None,
        )
        
        # 4. Gerar tokens
        tokens = AuthService._generate_tokens(user)
        
        return RegisterResponse(
            message="Conta criada com sucesso",
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user).model_dump(),
            tenant=TenantResponse.model_validate(tenant).model_dump(),
        )
    
    # ==================== REFRESH TOKEN ====================
    
    @staticmethod
    def refresh_token(db: Session, *, refresh_token: str) -> TokenResponse:
        """
        Renova access token usando refresh token.
        
        Raises:
            InvalidRefreshTokenError: Token inválido ou expirado
            AccountDisabledError: Usuário desativado
            TenantSuspendedError: Tenant suspenso
        """
        try:
            payload = decode_token(refresh_token)
            
            # Validar tipo do token
            if payload.get("type") != "refresh":
                raise InvalidRefreshTokenError()
            
            user_id = payload.get("sub")
            
            if not user_id:
                raise InvalidRefreshTokenError()
                
        except JWTError:
            raise InvalidRefreshTokenError()
        
        # Buscar usuário
        import uuid
        user = UserRepository.get_by_id(db, uuid.UUID(user_id))
        
        if not user:
            raise InvalidRefreshTokenError()
        
        if not user.is_active:
            raise AccountDisabledError()
        
        # Verificar tenant
        tenant = TenantRepository.get_by_id(db, user.tenant_id)
        
        if not tenant or not tenant.is_active:
            raise TenantSuspendedError()
        
        # Gerar novo access token (não gera novo refresh)
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "tenant_id": str(user.tenant_id),
                "role": user.role,
            }
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # Retorna o mesmo refresh
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    
    # ==================== VERIFY ====================
    
    @staticmethod
    def verify_token(token: str) -> VerifyResponse:
        """
        Verifica se token é válido e retorna payload.
        
        Raises:
            InvalidRefreshTokenError: Token inválido
        """
        try:
            payload = decode_token(token)
            
            return VerifyResponse(
                valid=True,
                user_id=payload.get("sub", ""),
                tenant_id=payload.get("tenant_id", ""),
                role=payload.get("role", ""),
                expires_at=payload.get("exp", 0),
            )
            
        except JWTError:
            raise InvalidRefreshTokenError()
    
    # ==================== HELPERS ====================
    
    @staticmethod
    def _generate_tokens(user: User) -> dict:
        """Gera par de tokens para o usuário."""
        token_data = {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role,
        }
        
        return {
            "access_token": create_access_token(data=token_data),
            "refresh_token": create_refresh_token(data={"sub": str(user.id)}),
        }
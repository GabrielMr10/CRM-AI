"""
Configurações centralizadas da aplicação.
Carrega variáveis do .env e valida com Pydantic.

USO:
    from app.core.config import settings
    print(settings.PROJECT_NAME)
    print(settings.SQLALCHEMY_DATABASE_URI)
"""
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações carregadas do ambiente.
    Pydantic valida tipos automaticamente.
    """
    
    # ==================== PROJETO ====================
    PROJECT_NAME: str = "CRM Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # ==================== BANCO DE DADOS ====================
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "crm_user"
    POSTGRES_PASSWORD: str = "crm_password"
    POSTGRES_DB: str = "crm_db"
    POSTGRES_PORT: int = 5432
    
    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Monta a URL de conexão PostgreSQL automaticamente."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # ==================== SEGURANÇA JWT ====================
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"  # openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ==================== CORS ====================
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = "*"
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """
        Converte string separada por vírgula em lista.
        Aceita: "*" ou "http://localhost,http://app.com"
        """
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # ==================== INTEGRAÇÕES (futuro) ====================
    N8N_WEBHOOK_URL: str | None = None
    ZAPI_INSTANCE_ID: str | None = None
    ZAPI_TOKEN: str | None = None
    
    # ==================== PYDANTIC CONFIG ====================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignora variáveis extras no .env
    )


# Instância global - importar de qualquer lugar
settings = Settings()
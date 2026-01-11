"""
Configuração do SQLAlchemy.
Engine, sessão e classe base para models.

USO:
    from app.db.session import Base, SessionLocal
    
    class User(Base):
        __tablename__ = "users"
        ...
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Engine - conexão com PostgreSQL
# pool_pre_ping=True verifica conexão antes de usar (evita erros de conexão morta)
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=10,          # Conexões mantidas abertas
    max_overflow=20,       # Conexões extras permitidas em pico
    echo=False,            # True para debug SQL (verbose!)
)

# Fábrica de sessões
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Classe base para todos os models
Base = declarative_base()
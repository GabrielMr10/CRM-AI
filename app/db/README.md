# DB Module

## Responsabilidade
Configuração do SQLAlchemy: engine, sessão e classe base para models.

## Arquivos
| Arquivo | Função |
|---------|--------|
| `session.py` | Engine e SessionLocal |
| `base.py` | Importa todos os models (para Alembic detectar) |

## Dependências
- `app.core.config` - Para SQLALCHEMY_DATABASE_URI

## Usado por
- `app.core.dependencies` - get_db
- `alembic/env.py` - Migrations
- Todos os repositories dos módulos
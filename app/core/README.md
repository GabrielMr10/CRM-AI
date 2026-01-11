# Core Module

## Responsabilidade
Configurações globais, segurança JWT, exceções HTTP e injeção de dependências.
Este módulo é a FUNDAÇÃO - todos os outros módulos dependem dele.

## Arquivos
| Arquivo | Função |
|---------|--------|
| `config.py` | Variáveis de ambiente (Pydantic Settings) |
| `security.py` | Hash de senha e criação/validação JWT |
| `exceptions.py` | Exceções HTTP customizadas reutilizáveis |
| `dependencies.py` | Injeção de dependências FastAPI (get_db, get_current_user) |

## Dependências externas
- `app.db.session` - Para get_db dependency

## Usado por
- Todos os módulos do sistema

## Variáveis de ambiente necessárias
- SECRET_KEY (obrigatório)
- ALGORITHM (default: HS256)
- ACCESS_TOKEN_EXPIRE_MINUTES (default: 30)
- REFRESH_TOKEN_EXPIRE_DAYS (default: 7)
- POSTGRES_* (conexão com banco)
# Módulo: Users

## Responsabilidade
Gerenciar usuários do sistema. Cada usuário pertence a um tenant e tem um role.

## Dependências
- `app.core` - Config, security, exceptions
- `app.db` - Base, SessionLocal
- `app.modules.tenants` - Tenant model (FK)

## Dependido por
- `app.core.dependencies` - get_current_user
- `app.modules.auth` - Login/registro
- Todos os módulos que precisam do usuário logado

## Endpoints
| Método | Rota | Descrição | Permissão |
|--------|------|-----------|-----------|
| GET | /users/me | Dados do usuário logado | Autenticado |
| PATCH | /users/me | Atualiza próprio perfil | Autenticado |
| GET | /users | Lista usuários do tenant | Admin |
| POST | /users | Cria usuário no tenant | Admin |
| GET | /users/{id} | Detalhe usuário | Admin |
| PATCH | /users/{id} | Atualiza usuário | Admin |
| DELETE | /users/{id} | Remove usuário | Admin |

## Models
- `User` - Tabela principal

## Roles disponíveis
- `owner` - Dono do tenant (criado no signup)
- `admin` - Administrador (gerencia usuários)
- `manager` - Gerente (acesso completo aos dados)
- `member` - Membro (acesso limitado)

## Regras de negócio
- Email único por tenant (mesmo email pode existir em tenants diferentes)
- Owner não pode ser removido
- Usuário só vê/edita usuários do próprio tenant# Módulo: Users

## Responsabilidade
Gerenciar usuários do sistema. Cada usuário pertence a um tenant e tem um role.

## Dependências
- `app.core` - Config, security, exceptions
- `app.db` - Base, SessionLocal
- `app.modules.tenants` - Tenant model (FK)

## Dependido por
- `app.core.dependencies` - get_current_user
- `app.modules.auth` - Login/registro
- Todos os módulos que precisam do usuário logado

## Endpoints
| Método | Rota | Descrição | Permissão |
|--------|------|-----------|-----------|
| GET | /users/me | Dados do usuário logado | Autenticado |
| PATCH | /users/me | Atualiza próprio perfil | Autenticado |
| GET | /users | Lista usuários do tenant | Admin |
| POST | /users | Cria usuário no tenant | Admin |
| GET | /users/{id} | Detalhe usuário | Admin |
| PATCH | /users/{id} | Atualiza usuário | Admin |
| DELETE | /users/{id} | Remove usuário | Admin |

## Models
- `User` - Tabela principal

## Roles disponíveis
- `owner` - Dono do tenant (criado no signup)
- `admin` - Administrador (gerencia usuários)
- `manager` - Gerente (acesso completo aos dados)
- `member` - Membro (acesso limitado)

## Regras de negócio
- Email único por tenant (mesmo email pode existir em tenants diferentes)
- Owner não pode ser removido
- Usuário só vê/edita usuários do próprio tenant
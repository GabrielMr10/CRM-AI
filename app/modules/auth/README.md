# Módulo: Auth

## Responsabilidade
Autenticação e autorização. Login, registro, refresh token.

## Dependências
- `app.core.security` - JWT, hash de senha
- `app.modules.tenants` - Criar tenant no registro
- `app.modules.users` - Criar/validar usuário

## Endpoints
| Método | Rota | Descrição | Permissão |
|--------|------|-----------|-----------|
| POST | /auth/register | Cria tenant + user owner | Público |
| POST | /auth/login | Retorna access + refresh token | Público |
| POST | /auth/refresh | Renova access token | Público (com refresh token) |
| POST | /auth/logout | Invalida refresh token | Autenticado |
| GET | /auth/verify | Verifica se token é válido | Autenticado |

## Fluxo de Registro
1. Recebe dados do tenant + usuário
2. Valida email/slug únicos
3. Cria Tenant
4. Cria User com role=OWNER vinculado ao tenant
5. Gera tokens e retorna

## Fluxo de Login
1. Recebe email + senha
2. Busca usuário por email (global)
3. Valida senha
4. Verifica se tenant está ativo
5. Atualiza last_login
6. Gera tokens com tenant_id no payload

## Payload do JWT
```json
{
  "sub": "user_uuid",
  "tenant_id": "tenant_uuid",
  "role": "owner",
  "type": "access",
  "exp": 1234567890
}
```
# Teste Manual do Swagger UI - Autenticação OAuth2

## Status da Correção: ✅ IMPLEMENTADO

### Mudanças Realizadas:

1. **app/core/dependencies.py** - Linha 31
   ```python
   oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login/form")
   ```

2. **app/modules/auth/router.py** - Linha 78
   ```python
   include_in_schema=True  # Visível para Swagger UI usar no Authorize
   ```

### Como Testar no Swagger UI:

#### Passo 1: Acessar o Swagger UI
```
URL: http://localhost:8000/docs
```

#### Passo 2: Clicar no botão "Authorize" (🔓 canto superior direito)

#### Passo 3: Preencher o formulário OAuth2
- **username**: `owner@company.com`
- **password**: `SecurePass123!`
- **client_id**: (deixar vazio)
- **client_secret**: (deixar vazio)

#### Passo 4: Clicar em "Authorize"

### Resultado Esperado:

✅ **Sucesso**: Modal fecha e o ícone muda de 🔓 para 🔒
✅ **Token armazenado**: Todas as requisições agora incluem `Authorization: Bearer <token>`
✅ **Endpoints protegidos**: Agora podem ser testados (ex: GET /api/v1/users/)

### Testes Automatizados (via curl):

#### Teste 1: Form Login (simula Swagger Authorize)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login/form" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=owner@company.com&password=SecurePass123!"
```

**Resultado**: ✅ Retorna `access_token` e `token_type: bearer`

#### Teste 2: Usar token em endpoint protegido
```bash
TOKEN="<access_token_do_passo_anterior>"
curl -X GET "http://localhost:8000/api/v1/users/" \
  -H "Authorization: Bearer $TOKEN"
```

**Resultado**: ✅ Retorna lista de usuários do tenant

### Verificação OpenAPI:

```bash
curl -s http://localhost:8000/api/v1/openapi.json | grep -A 5 "tokenUrl"
```

**Resultado Esperado**:
```json
{
  "tokenUrl": "/api/v1/auth/login/form"
}
```

### Arquitetura da Solução:

```
┌─────────────────┐
│   Swagger UI    │
│  (Authorize 🔓) │
└────────┬────────┘
         │ POST /api/v1/auth/login/form
         │ Content-Type: application/x-www-form-urlencoded
         │ Body: username=...&password=...
         ▼
┌─────────────────────────┐
│  FastAPI Router         │
│  OAuth2PasswordRequest  │
│  Form (username/pwd)    │
└────────┬────────────────┘
         │ Converte para LoginRequest(email, password)
         ▼
┌─────────────────┐
│  AuthService    │
│  login(db, data)│
└────────┬────────┘
         │ Valida credenciais
         │ Gera JWT tokens
         ▼
┌─────────────────────┐
│   AuthResponse      │
│  - access_token     │
│  - token_type       │
│  - user, tenant     │
└─────────────────────┘
```

### Troubleshooting:

**Problema**: Ainda recebo 422 Unprocessable Entity

**Solução**:
1. Verificar se o backend foi reiniciado após as mudanças
2. Limpar cache do navegador (Ctrl+Shift+Del)
3. Verificar se está usando `username` (não `email`) no campo do Swagger
4. Confirmar que o endpoint `/login/form` está visível no Swagger docs

**Comando para reiniciar**:
```bash
docker-compose restart backend
```

### Credenciais de Teste:

| Campo | Valor |
|-------|-------|
| username | `owner@company.com` |
| password | `SecurePass123!` |
| Tenant | Acme Corporation |
| Role | owner |

---

**Data da Correção**: 2026-01-14
**Status**: ✅ Pronto para teste manual via Swagger UI
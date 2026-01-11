# Módulo: Tenants (Multi-tenancy)

## Responsabilidade
Gerenciar tenants (empresas/clientes) do SaaS. Cada tenant é isolado e tem suas próprias configurações.

## Dependências
- `app.core` - Config, security, exceptions
- `app.db` - Base, SessionLocal

## Dependido por
- `app.modules.users` - Usuário pertence a um tenant
- `app.modules.leads` - Lead pertence a um tenant
- Todos os módulos de negócio

## Endpoints
| Método | Rota | Descrição | Permissão |
|--------|------|-----------|-----------|
| POST | /tenants | Cria tenant (signup) | Público |
| GET | /tenants/me | Dados do tenant atual | Autenticado |
| PATCH | /tenants/me | Atualiza tenant | Admin do tenant |
| GET | /tenants | Lista todos tenants | Superuser |
| GET | /tenants/{id} | Detalhe tenant | Superuser |
| DELETE | /tenants/{id} | Remove tenant | Superuser |

## Models
- `Tenant` - Tabela principal com configurações

## Fluxo de criação
1. Usuário faz signup → cria Tenant + User admin
2. Tenant recebe slug único (subdomínio futuro)
3. Configurações de plano são definidas

## Campos importantes
- `slug` - Identificador único (usado em URLs)
- `plan` - Plano de assinatura
- `is_active` - Tenant ativo/suspenso
- `settings` - JSONB com configs flexíveis
- `n8n_instance_url` - URL da instância n8n do cliente
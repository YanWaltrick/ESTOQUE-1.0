# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos essenciais

```bash
# Desenvolvimento local
python app.py                   # Inicia servidor em localhost:5000 (debug mode se FLASK_ENV=development)
python wsgi.py                  # Inicia com WSGI (waitress/gunicorn)

# Dependências
pip install -r requirements.txt

# Migrations (via manage.py)
flask --app manage db migrate -m "descrição"   # Gera nova migração
flask --app manage db upgrade                  # Aplica migrações
flask --app manage db downgrade                # Reverte última migração
```

## Configuração de ambiente

Copie `.env.example` para `.env` e preencha os valores. As variáveis obrigatórias para desenvolvimento mínimo:

```env
FLASK_ENV=development
SECRET_KEY=qualquer-chave-para-dev
# DATABASE_URL não é obrigatório — usa SQLite em instance/estoque.sqlite por padrão
```

Para produção, `SECRET_KEY` é obrigatória (levanta `RuntimeError` se ausente com `FLASK_ENV != development`).

Variáveis opcionais relevantes (ver `.env.example` para lista completa):

```env
ADMIN_EMAILS=admin@example.com,outro@example.com  # Destinatários de e-mail de chamados
SESSION_COOKIE_SECURE=True                         # Ativar em produção com HTTPS
SESSION_COOKIE_SAMESITE=Lax
APP_PUBLIC_BASE_URL=https://app.exemplo.com        # Para imagens em notificações Teams
TEAMS_CHANNEL_WEBHOOK_URL=                         # Webhook de canal Teams
POWER_AUTOMATE_WEBHOOK_URL=                        # Fallback legado via Power Automate
# Entra ID (SSO Microsoft — deixar em branco se não usar)
ENTRA_CLIENT_ID=
ENTRA_CLIENT_SECRET=
ENTRA_TENANT_ID=
```

## Arquitetura

### Application Factory

`app/__init__.py` exporta `create_app()`, que:
1. Chama `app/database.py:create_app()` para criar a instância Flask, SQLAlchemy e Flask-Mail
2. Configura `CSRFProtect`, `LoginManager` e session timeout de 10 min para não-admins
3. Registra `after_request` com cabeçalhos de segurança (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, HSTS em produção)
4. Registra os blueprints
5. Executa `init_database()` dentro do app context, que aplica migrations, roda `db.create_all()`, e cria o usuário admin padrão (`admin`/`admin`) se não existir

### Blueprints e rotas

| Blueprint | Prefixo | Arquivo | Responsabilidade |
|-----------|---------|---------|-----------------|
| `auth_bp` | `/` | `app/routes/auth.py` | Login, logout, recuperação de senha |
| `main_bp` | `/` | `app/routes/main.py` | Dashboard, estoque, chamados, documentos, perfil |
| `admin_bp` | `/` | `app/routes/admin.py` | Gerenciamento de usuários, relatórios |
| `api_bp` | `/api` | `app/routes/api.py` | API JSON para operações assíncronas do frontend |
| `entra_bp` | `/` | `app/routes/entra_auth.py` | Login SSO via Microsoft Entra ID (opcional) |

### Modelos (todos em `app/models/__init__.py`)

- **`User`** — RBAC com dois roles: `admin` e `usuario`. Suporte a CLT e PJ. Controla bloqueio por tentativas de login (5 tentativas → bloqueio de 15 min). Fuso horário GMT-3 em todos os timestamps.
- **`Produto` / `Movimentacao` / `Categoria`** — Núcleo do controle de estoque.
- **`Chamada`** — Tickets/chamados de usuários para admins, com notificação por e-mail e webhook (Teams/Power Automate).
- **`Historico`** — Log de auditoria de ações relevantes.
- **`DocumentoUsuario`** — Metadados de arquivos enviados a usuários; o arquivo fica em disco (`static/uploads/documentos/`).
- **`DocumentoArquivo`** — Armazena conteúdo binário de documentos diretamente no banco (coluna `LargeBinary`).
- **`ItemRecebido`** — Itens entregues a colaboradores.
- **`TermoEntrega`** — Termo de Entrega e Responsabilidade gerado automaticamente ao criar usuário; suporta CLT e PJ. Gerado como PDF via ReportLab (`app/services/termo_service.py`).

### RBAC (app/auth/decorators.py)

Três decoradores para proteger rotas:
- `@require_role('admin')` — verifica o campo `role` do usuário; aceita múltiplos roles: `@require_role('admin', 'usuario')`
- `@require_permission('delete_user')` — verifica permissão específica via `ROLES_PERMISSIONS`
- `@require_authenticated()` — apenas garante que o usuário está autenticado

A função `can_perform(permission)`, `get_user_permissions()` e o dict `ROLES_PERMISSIONS` são injetados em todos os templates via context processor.

### Segurança (app/auth/security.py)

`PasswordValidator` valida complexidade de senhas (mínimo 6 chars, maiúsculas, minúsculas, dígito). `validate_email` valida formato de e-mail. Ambos usados no cadastro e notificações.

### Banco de dados

- **Desenvolvimento:** SQLite em `instance/estoque.sqlite` (padrão automático)
- **Produção:** MySQL via `DATABASE_URL=mysql+pymysql://...`
- O sistema aplica migrations do Alembic na inicialização. Colunas ausentes em tabelas existentes são adicionadas por `_ensure_schema_columns()` como fallback manual.
- Não há testes automatizados no projeto; o banco é sempre inicializado pelo código da aplicação.

### Uploads

Arquivos ficam em `static/uploads/` com subdiretórios: `avatars/`, `chamadas/`, `documentos/`, `documentos/termos/`. As pastas são criadas automaticamente na inicialização.

### Notificações externas

`app/services/notification_service.py` dispara notificações via:
- **Flask-Mail** (SMTP) para e-mails de chamados; destinatários em `ADMIN_EMAILS`
- **Webhook HTTP** para Microsoft Teams (`TEAMS_CHANNEL_WEBHOOK_URL`) ou Power Automate (`POWER_AUTOMATE_WEBHOOK_URL`) como fallback

### Logging

`app/utils/logger.py` provê logging centralizado (`criar_logger`, `registrar_erro`, `registrar_seguranca`). Logs vão para arquivo e console com timestamps GMT-3.

### Deploy

CI/CD via GitHub Actions (`.github/workflows/main_somasgt.yml`) faz push automático para **Azure App Service** (app name: `SOMASGT`) a cada push na branch `main`.

### Scripts utilitários

Scripts em `scripts/` para tarefas administrativas: `import_users.py` (importação em lote), `update_users.py`, `update_emails.py`, `migrate_docs_to_db.py` (migração de arquivos do disco para o banco), `alter_blob.py`, etc. Não fazem parte do fluxo normal da aplicação. Devem ser executados a partir da raiz do projeto (ex.: `python scripts/import_users.py ...`).

### Documentação

A documentação fica em `docs/` (índice em `docs/README.md`): `ANALISE_CLT_PJ.md`, `SETUP_REMOTO.md`, `SECURITY.md` e a subpasta `docs/entra-id/` com os guias da integração Microsoft Entra ID. O `README.md` e este `CLAUDE.md` permanecem na raiz.

### Testes

Testes e verificações ficam em `tests/` (ex.: `tests/test_entra_id.py`, smoke test da integração Entra ID). Executar a partir da raiz: `python tests/test_entra_id.py`.

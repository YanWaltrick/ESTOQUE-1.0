# Arquitetura — Sistema ESTOQUE

Visão geral em fluxogramas. O detalhamento de cada componente está no `CLAUDE.md` (raiz)
e na própria estrutura de `app/`. Este documento explica *como as peças se conectam* —
não substitui a leitura do código.

## 1. Arquitetura e inicialização

```mermaid
flowchart TD
    subgraph ENTRY["Entrypoints"]
        A1["app.py<br/>(dev — localhost:5000)"]
        A2["wsgi.py<br/>(prod — waitress/gunicorn)"]
        A3["manage.py<br/>(CLI de migrations)"]
    end

    A1 & A2 --> FAC["create_app()<br/>app/__init__.py"]

    FAC --> DB0["database.py<br/>Flask + SQLAlchemy + Mail"]
    FAC --> SEC["CSRFProtect · LoginManager<br/>session timeout 10min (não-admin)<br/>after_request: headers de segurança"]
    FAC --> BP["Registro de Blueprints"]
    FAC --> INIT["init_database()<br/>migrations + create_all()<br/>cria admin/admin"]

    BP --> R1["auth_bp /<br/>login, logout, recuperação"]
    BP --> R2["main_bp /<br/>dashboard, estoque, chamados, docs, perfil"]
    BP --> R3["admin_bp /<br/>usuários, relatórios"]
    BP --> R4["api_bp /api<br/>JSON assíncrono"]
    BP --> R5["entra_bp /<br/>SSO Entra ID (opcional)"]

    R1 & R2 & R3 & R4 & R5 --> DEC["RBAC<br/>app/auth/decorators.py<br/>@require_role / @require_permission"]

    DEC --> SVC["Services<br/>estoque · notification · termo"]
    SVC --> MOD["Models<br/>app/models/__init__.py"]
    MOD --> DBX[("SQLite (dev)<br/>MySQL (prod)")]

    SVC -.->|e-mail / webhook| EXT["SMTP · Teams · Power Automate"]
    SVC -.->|PDF ReportLab| PDF["Termo de Entrega"]

    INIT --> DBX
```

## 2. Fluxo de uma requisição

```mermaid
flowchart TD
    U["Usuário / Navegador"] --> REQ["Requisição HTTP"]
    REQ --> CSRF{"CSRF válido?<br/>(POST)"}
    CSRF -->|não| ERR1["400 / rejeitado"]
    CSRF -->|sim| AUTH{"Autenticado?<br/>LoginManager"}
    AUTH -->|não| LOGIN["Redireciona p/ login<br/>(tradicional ou Entra ID)"]
    AUTH -->|sim| TIMEOUT{"Sessão expirada?<br/>(10min não-admin)"}
    TIMEOUT -->|sim| LOGIN
    TIMEOUT -->|não| ROLE{"RBAC<br/>role / permissão ok?"}
    ROLE -->|não| ERR2["403 Forbidden"]
    ROLE -->|sim| HANDLER["Handler do Blueprint"]
    HANDLER --> SERVICE["Service (regra de negócio)"]
    SERVICE --> MODEL["Model + SQLAlchemy"]
    MODEL --> DB[("Banco de dados")]
    SERVICE --> HIST["Historico<br/>(log de auditoria)"]
    HANDLER --> RESP["Resposta<br/>HTML (Jinja) ou JSON"]
    RESP --> HEADERS["after_request<br/>headers de segurança + HSTS"]
    HEADERS --> U
```

## 3. Fluxo de autenticação SSO (Entra ID)

```mermaid
flowchart LR
    C["Clica 'Entrar com Microsoft'"] --> L["GET /entra/login<br/>gera CSRF (state)"]
    L --> MS["login.microsoftonline.com<br/>usuário autentica"]
    MS --> CB["GET /entra/callback?code&state"]
    CB --> V1{"CSRF ok?"}
    V1 -->|não| X1["Erro"]
    V1 -->|sim| TOK["Troca código por token<br/>(usa CLIENT_SECRET)"]
    TOK --> GRAPH["Busca dados via Microsoft Graph"]
    GRAPH --> V2{"E-mail existe<br/>e usuário ativo no BD?"}
    V2 -->|não| X2["Acesso negado"]
    V2 -->|sim| SESS["Popula sessão Flask"]
    SESS --> HOME["Redireciona p/ página principal"]
```

Detalhes do SSO em [entra-id/README.md](entra-id/README.md) e [entra-id/SETUP.md](entra-id/SETUP.md).

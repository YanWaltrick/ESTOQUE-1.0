# Testes Automatizados — Sistema ESTOQUE

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
>
> **Última atualização:** 2026-06-29 — integração do upstream (Entra ID reescrito; testes de Entra ID removidos)

Visão geral da suíte de testes automatizados do projeto. As **pendências e
próximos passos** ficam em [`ROADMAP.md`](ROADMAP.md); o histórico de revisões de
código fica em [`REVISAO_CODIGO.md`](REVISAO_CODIGO.md).

> **Banco de teste: MySQL.** A suíte roda contra o banco `estoque_test` no container
> MySQL (`docker compose up -d`) — mesmo dialeto de produção. O isolamento entre
> testes usa transação externa real (receita do Flask-SQLAlchemy), não o workaround
> do pysqlite. Ver [Plano de Padronização MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md).

---

## 1. Estado atual

| Item | Status |
|------|--------|
| Framework de testes (`pytest`) configurado | 🟢 Concluído |
| Fixtures base (`conftest.py`) — app, banco isolado, client autenticado | 🟢 Concluído |
| Fixtures auxiliares (`criar_usuario`, `usuario_comum`, `user_client`) | 🟢 Concluído |
| Testes de fumaça do fluxo de login | 🟢 Concluído (4 testes) |
| Cobertura das rotas/serviços | 🟢 **73%** (266 testes) |
| Gate de CI rodando `pytest` | 🔴 Pendente — ver [ROADMAP](ROADMAP.md#1-gate-de-ci) |

**Cobertura atual: 73%** (`pytest --cov=app`), partindo de 22%. A suíte cobre os
modelos, os serviços (estoque, notificações, geração de PDF do termo), as rotas
JSON (`/api`), administrativas (`/admin`) e de autenticação/perfil. Os fluxos de maior risco do
[ROADMAP](ROADMAP.md#2-cobertura-das-rotas-de-maior-risco) — bloqueio por força
bruta, RBAC, geração do Termo (CLT/PJ), estoque e API — estão cobertos.

> **Achados durante a escrita dos testes** (corrigidos na mesma branch):
> - **Bug de bloqueio por força bruta:** `User.pode_tentar_login`/`is_active`/
>   `minutos_ate_desbloqueio` comparavam `datetime` *aware* (GMT-3) com o valor
>   *naive* lido do MySQL, levantando `TypeError` — qualquer login de conta já
>   bloqueada dava erro 500. Corrigido com `_garantir_aware_gmt3` em `app/models`.
> - **Bug de status HTTP na API:** em `criar_usuario_api`, a validação de e-mail
>   retornava `jsonify({...}, 400)` (status 200, corpo malformado) em vez de
>   `jsonify({...}), 400`. Corrigido.
> - **Rotas órfãs:** `/admin/dashboard` e `/admin/audit-log` referenciam templates
>   inexistentes (`admin/dashboard.html`, `admin/audit_log.html`) e não têm links;
>   levantam `TemplateNotFound`. Documentado nos testes; remoção/implementação
>   pendente (ver [ROADMAP](ROADMAP.md)).

---

## 2. Como rodar

A partir da raiz do projeto (com o MySQL de pé):

```bash
docker compose up -d                  # MySQL local (cria estoque_test)
pip install -r requirements-dev.txt   # pytest + pytest-cov
pytest                                # roda toda a suíte
pytest --cov=app                      # com relatório de cobertura
pytest tests/test_smoke.py -v         # um arquivo específico
```

> Requer as dependências do projeto instaladas (`requirements.txt`). Em um
> ambiente novo, use um virtualenv: `python -m venv .venv && source .venv/bin/activate`.

---

## 3. O padrão (fonte da verdade: `tests/conftest.py`)

O arquivo [`tests/conftest.py`](../../tests/conftest.py) **é** o padrão de testes.
Todo teste novo reutiliza as fixtures dele em vez de montar a própria app ou banco.

| Fixture | Escopo | O que entrega |
|---------|--------|---------------|
| `app` | sessão | App criada com `create_app()` sobre o MySQL `estoque_test` |
| `db_session` | função | Isola o teste em transação externa revertida ao final |
| `client` | função | `test_client()` sem autenticação |
| `auth_client` | função | `test_client()` já logado como admin padrão (`admin`/`admin`) |
| `criar_usuario` | função | Factory de usuário de teste com senha conhecida (`SENHA_TESTE`); demais kwargs vão para o construtor de `User` |
| `usuario_comum` | função | Um usuário `role='usuario'` persistido para o teste |
| `user_client` | função | `test_client()` logado como o `usuario_comum` (para testar RBAC/fluxos de não-admin) |

> Há ainda o fixture autouse `_limpar_uploads_de_teste` (escopo de sessão), que
> remove os arquivos gravados em `static/uploads/` pelos testes de upload/PDF —
> nenhum teste precisa invocá-lo.

**Decisões de arquitetura relevantes:**

- O banco de teste é selecionado definindo `DATABASE_URL` em variável de ambiente
  **antes** de importar a aplicação — porque `app/database.py` resolve a URL no
  momento do import. Isso mantém o banco de teste (`estoque_test`) separado do de dev.
- `create_app()` chama `init_database()` na criação (cria tabelas + admin padrão).
  Há revisões Alembic em `migrations/versions/`, aplicadas no boot, com
  `db.create_all()` + `_ensure_schema_columns()` como complemento. O isolamento dos
  testes deve ser revalidado contra esse caminho — ver
  [ROADMAP](ROADMAP.md#3-revalidar-isolamento-da-suíte-com-as-migrações-alembic).
- `WTF_CSRF_ENABLED=False` na config de teste permite POSTs sem token CSRF.

**Ao escrever um teste novo, copie o estilo de
[`tests/test_smoke.py`](../../tests/test_smoke.py):** nomes em português `test_*`,
asserts sobre status/redirecionamento, uma camada por teste.

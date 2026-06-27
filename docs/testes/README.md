# Testes Automatizados — Sistema ESTOQUE

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
>
> **Última atualização:** 2026-06-27 — branch `feature/implementacao-testes`

Visão geral da suíte de testes automatizados do projeto. As **pendências e
próximos passos** ficam em [`ROADMAP.md`](ROADMAP.md); o histórico de revisões de
código fica em [`REVISAO_CODIGO.md`](REVISAO_CODIGO.md).

> ⚠️ **Interino:** a suíte roda hoje em SQLite e o isolamento entre testes está
> **quebrado** (limitação do driver pysqlite — comprovado). A direção decidida é
> migrar para **MySQL** (mesmo dialeto de produção), o que conserta o isolamento de
> forma limpa. Ver [Plano de Padronização MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md)
> — planejado, ainda não implementado.

---

## 1. Estado atual

| Item | Status |
|------|--------|
| Framework de testes (`pytest`) configurado | 🟢 Concluído |
| Fixtures base (`conftest.py`) — app, banco isolado, client autenticado | 🟢 Concluído |
| Testes de fumaça do fluxo de login | 🟢 Concluído (4 testes) |
| Gate de CI rodando `pytest` | 🔴 Pendente — ver [ROADMAP](ROADMAP.md#1-gate-de-ci) |
| Cobertura das rotas críticas | 🔴 Pendente — ver [ROADMAP](ROADMAP.md#2-cobertura-das-rotas-de-maior-risco) |

Cobertura atual: apenas o caminho de autenticação (login/redirect). O restante da
aplicação ainda **não** tem testes.

---

## 2. Como rodar

A partir da raiz do projeto:

```bash
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
| `app` | sessão | App criada com `create_app()` sobre um SQLite temporário |
| `db_session` | função | Isola o teste em transação revertida ao final (savepoint) |
| `client` | função | `test_client()` sem autenticação |
| `auth_client` | função | `test_client()` já logado como admin padrão (`admin`/`admin`) |

**Decisões de arquitetura relevantes:**

- O banco de teste é selecionado definindo `DATABASE_URL` em variável de ambiente
  **antes** de importar a aplicação — porque `app/database.py` resolve a URL no
  momento do import. Isso mantém o banco de teste isolado de `instance/estoque.sqlite`.
- `create_app()` chama `init_database()` na criação (cria tabelas + admin padrão).
  Hoje não há revisões Alembic, então cai em `db.create_all()`. **Quando a primeira
  migração for criada, o isolamento precisa ser revalidado** — ver
  [ROADMAP](ROADMAP.md#3-revalidar-isolamento-com-a-primeira-migração-alembic).
- `WTF_CSRF_ENABLED=False` na config de teste permite POSTs sem token CSRF.

**Ao escrever um teste novo, copie o estilo de
[`tests/test_smoke.py`](../../tests/test_smoke.py):** nomes em português `test_*`,
asserts sobre status/redirecionamento, uma camada por teste.

---

## 4. Relação com o smoke test legado

O arquivo `tests/test_entra_id.py` é um smoke test antigo baseado em `print`
(validação de imports da integração Entra ID). Continua executável via
`python tests/test_entra_id.py`, mas **novos testes seguem o padrão pytest** acima.
Migrá-lo para pytest é um item de baixa prioridade no [ROADMAP](ROADMAP.md).

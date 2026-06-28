# Registro de Revisões de Código — Testes

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> Log acumulativo das revisões de código da área de testes. Cada entrada registra
> escopo, achados e o destino de cada achado (corrigido ou virou item no
> [ROADMAP](ROADMAP.md)).
>
> **Última atualização:** 2026-06-27 — revisão `xhigh` com correções aplicadas

---

## 2026-06-27 — Revisão `xhigh` do fork + correções aplicadas

**Escopo:** diff do fork desde o merge do upstream (`1e577a0..HEAD`) — além dos
testes, os scripts movidos para `scripts/`. A maior parte do diff é documentação;
o foco foi o código com risco real.

**Método:** `/code-review xhigh` (recall) com **verificação empírica**: a suíte foi
de fato executada (`.venv` + `requirements-dev.txt`) e cada achado foi reproduzido
com um teste descartável **antes** de corrigir.

**Resultado:** 3 defeitos confirmados, **todos corrigidos nesta tarefa**. O achado
X1 reabre e **corrige o diagnóstico** do achado R1 da revisão `high` anterior.

### Achados e correções

| # | Severidade | Verificação | Local | Correção |
|---|-----------|-------------|-------|----------|
| X1 | 🔴 Alta | CONFIRMADO (reproduzido) | `tests/conftest.py` (`db_session`) | Receita oficial do Flask-SQLAlchemy (troca engine→conexão) |
| X2 | 🟠 Média | CONFIRMADO (reproduzido) | `tests/test_entra_id.py` via `pytest.ini` | `collect_ignore` no `conftest.py` |
| X3 | 🔴 Alta | CONFIRMADO (reproduzido) | `scripts/migrate_docs_to_db.py` | Ver [revisão de banco-de-dados](../banco-de-dados/REVISAO_CODIGO.md) |

**X1 — `db_session` não isolava de verdade (corrige o diagnóstico de R1).**
A revisão `high` anterior (R1) previu `StatementError` por *bind* global apontando
para conexão fechada. A reprodução empírica revelou um sintoma **diferente e pior**:
`_db.session.configure(bind=...)` é **ignorado** pelo Flask-SQLAlchemy 3.x — seu
`get_bind` resolve o engine padrão por `engines[None]` e nunca chega ao
`super().get_bind()` que honraria o *bind* da sessão. Logo, os `commit()` dos testes
iam direto ao SQLite e **vazavam entre testes** (provado: um usuário criado em um
teste aparecia no seguinte). A suíte passava só porque nenhum smoke test dependia do
isolamento. **Correção:** adotada a receita oficial do FSQLA 3.1 (*join an external
transaction*) — cada engine é substituída por uma conexão com transação aberta no
dicionário `engines` e restaurada no teardown. Validado com sonda
(escreve-em-um-teste → ausente-no-seguinte), agora verde.

**X2 — `tests/test_entra_id.py` era importado pela coleta do pytest.**
Com `testpaths = tests` e `python_files = test_*.py`, o pytest importava o smoke
legado durante a coleta, executando seu corpo de módulo (`create_app()` + banner) e,
em caso de erro, `exit(1)` — contrariando o `CLAUDE.md`, que diz que ele deve rodar
só via `python tests/test_entra_id.py`. Provado com `pytest -s` (o banner aparecia na
saída). **Correção:** `collect_ignore = ["test_entra_id.py"]` no `conftest.py`.
Continua executável standalone e deixa de poluir/abortar a suíte. A migração completa
para pytest segue pendente no [ROADMAP #6](ROADMAP.md#6-migrar-smoke-test-legado-do-entra-id-para-pytest).

**X3 — script de migração de documentos não rodava.** Regressão de path introduzida
pelo *move* para `scripts/` somada a uma colisão de tabela pré-existente. Detalhe e
correção na [revisão de banco-de-dados](../banco-de-dados/REVISAO_CODIGO.md).

---

## 2026-06-27 — Revisão da base de testes (`/code-review high`)

**Escopo:** diff da branch `feature/implementacao-testes` — arquivos de teste e
configuração: `tests/conftest.py`, `tests/test_smoke.py`, `pytest.ini`,
`requirements-dev.txt`, `.gitignore`.

**Método:** revisão `high` (recall-biased) — varredura linha a linha, auditoria de
comportamento removido, rastreamento cross-file, reúso/simplificação/eficiência,
altitude e convenções do `CLAUDE.md`, com verificação de cada candidato contra o
código real.

**Resultado geral:** suíte **verde** (4 testes passando). Nenhum bug que quebre os
testes atuais. Dois achados **latentes** (não falham hoje, mas afetam testes
futuros) — ambos viraram itens no [ROADMAP](ROADMAP.md).

### Achados

| # | Severidade | Status verificação | Local | Destino |
|---|-----------|--------------------|-------|---------|
| R1 | 🔴 Alta | CONFIRMADO | `tests/conftest.py:66` | [ROADMAP #8](ROADMAP.md#8-db_session-deixa-bind-global-em-conexão-fechada-revisão-r1) |
| R2 | 🟡 Média | PLAUSÍVEL | `tests/conftest.py:33,50` | [ROADMAP #9](ROADMAP.md#9-limpeza-frágil-do-sqlite-temporário-revisão-r2) |

**R1 — `db_session` deixa *bind global* apontando para conexão fechada.**
O fixture reconfigura o sessionmaker compartilhado (escopo de sessão) com
`bind=connection`, mas no teardown a conexão é fechada e o bind nunca é resetado.
Qualquer teste futuro que use `client`/`auth_client`, toque o banco e **não**
dependa de `db_session`, rodando após um teste com `db_session`, abrirá sessão
presa à conexão fechada → `StatementError`. A suíte atual só escapa pela ordem dos
testes. Como o `conftest.py` é o padrão a ser copiado, o footgun se propaga.

**R2 — Limpeza frágil do arquivo SQLite temporário.**
O arquivo é criado no import do módulo; se a coleção falhar antes da fixture `app`,
vaza em `/tmp`. Além disso, o engine não é descartado antes do `os.remove`, o que
no Windows (suportado — há `tests/test_entra_id.bat`) causa `PermissionError` por
lock de conexões pooled.

### Pontos verificados como corretos (não são bugs)

- Override de `DATABASE_URL` antes do import + `load_dotenv(override=False)` blinda
  contra apontar para o MySQL de produção.
- `WTF_CSRF_ENABLED=False` setado após `create_app()` funciona (Flask-WTF lê em
  tempo de request) — confirmado pelos POSTs passando.
- `sqlite:///` + caminho absoluto gera URL válida (quatro barras).
- Asserts de redirect (`/admin?tab=chamadas`, `/login?next=`) batem com as rotas.
- Nenhuma violação das regras do `CLAUDE.md`.

# Registro de Revisões de Código — Testes

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> Log acumulativo das revisões de código da área de testes. Cada entrada registra
> escopo, achados e o destino de cada achado (corrigido ou virou item no
> [ROADMAP](ROADMAP.md)).
>
> **Última atualização:** 2026-06-27 — branch `feature/implementacao-testes`

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

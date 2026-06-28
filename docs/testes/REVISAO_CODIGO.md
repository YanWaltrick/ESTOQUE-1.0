# Registro de Revisões de Código — Testes

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> Log acumulativo das revisões de código da área de testes. Cada entrada registra
> escopo, achados e o destino de cada achado (corrigido ou virou item no
> [ROADMAP](ROADMAP.md)).
>
> **Última atualização:** 2026-06-28 — revisão `xhigh` da PR de cobertura, 13 correções aplicadas

---

## 2026-06-28 — Revisão `xhigh` da PR de cobertura (#3) + correções aplicadas

**Escopo:** diff da PR que subiu a cobertura de 22%→76% (`6ec184c^..6ec184c`) —
os 12 arquivos de teste novos, as fixtures do `conftest.py` e as 2 correções de
produção (`_garantir_aware_gmt3`, status da API). As duas correções originais da
PR foram confirmadas corretas; os achados abaixo são adicionais.

**Método:** `/code-review xhigh` (recall, 10 ângulos + verificação). Suíte
executada antes e depois: **289 testes passando** em ambos os pontos.

**Resultado:** 13 achados, **todos corrigidos nesta branch** (`fix/correcoes-revisao-cobertura`).
Itens de profundidade não triviais (TypeDecorator de fuso; decidir sobre as rotas
órfãs) foram **deixados no [ROADMAP](ROADMAP.md)** em vez de remendados.

### Achados e correções

| # | Tipo | Local | Correção |
|---|------|-------|----------|
| 1 | 🔴 Contrato de API | `app/__init__.py` + `tests/test_api.py` | `unauthorized_handler`: requisição de API/AJAX anônima agora recebe **401 JSON** (antes 302 HTML); teste endurecido para `== 401` |
| 2 | 🟠 Efeito colateral | `app/models/__init__.py` (`is_active`) | Propriedade de leitura não comita mais no banco; limpeza do bloqueio expirado fica só em `pode_tentar_login` |
| 3 | 🟠 Teste vacuous | `test_auth_routes.py` (`forgot_password`) | Passou a verificar que o `Chamada` foi de fato criado |
| 4 | 🟠 Teste vacuous | `test_auth_routes.py` (troca de senha) | Verifica que a senha mudou (sucesso) e que **não** mudou (senha atual errada) |
| 5 | 🟠 Teste vacuous | `test_auth_routes.py` (foto de perfil) | Verifica `foto_perfil` gravado no upload válido e ausente em extensão inválida/sem arquivo |
| 6–13 | 🟡 Qualidade | `conftest.py`, `test_*`, `models`, doc | Fixtures `admin_user`/`perfil_verificado_client` no `conftest`; hash da senha pré-computado; reuso de `now_gmt3()`/constante `GMT3`; `test_logger` robusto a estado global; doc deixa de copiar assinatura |

> Itens **não** corrigidos (achados de profundidade, deixados ao ROADMAP):
> generalizar o fuso na camada do ORM (achado de altitude) e decidir
> remover/implementar as rotas órfãs `/admin/dashboard` e `/admin/audit-log`
> (item #10).

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

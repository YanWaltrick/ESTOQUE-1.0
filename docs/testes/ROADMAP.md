# Roadmap de Testes — Pendências e Próximos Passos

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> Atualize o status e os checklists **na mesma tarefa** em que o trabalho for feito.
>
> **Última atualização:** 2026-06-30 — reconciliada a contagem de testes na tabela do item #2 (266 → **274**, a contagem real coletada pelo `pytest --collect-only`), alinhando-a ao cabeçalho. Antes (2026-06-29): item #1 (gate de CI) detalhado com as restrições concretas de implementação (service container MySQL, paridade de versão do Python com o deploy); suíte atual em 274 testes verdes; integração do upstream (Entra ID reescrito); testes de Entra ID removidos (289→266 testes, 76%→73%); item #6 encerrado

Origem da maioria destes itens: veredito do Conselho de LLMs sobre a estratégia de
testes (ver `## A Recomendação` / `## Pontos Cegos`). Os itens #8 e #9 vêm da
[Revisão de Código de 2026-06-27](REVISAO_CODIGO.md). O raciocínio do "porquê" está
preservado em cada item.

> ✅ **Banco de teste migrado para MySQL (2026-06-27):** o SQLite foi **removido**
> (100% MySQL). A suíte usa o banco `estoque_test` no container (`docker compose up`).
> Ver [Plano de Padronização MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md).
> Com isso, o item #9 (limpeza do SQLite temporário) deixou de existir e o #8
> (isolamento) foi corrigido pela receita de transação externa — válida no MySQL.
> Falta a **verificação da suíte contra o container** (E3) e o **gate de CI** (E7).

---

## Visão geral

| # | Item | Prioridade | Status |
|---|------|-----------|--------|
| 1 | Gate de CI rodando `pytest` | 🔺 Alta | 🔴 Pendente |
| 2 | Cobertura das rotas de maior risco | 🔺 Alta | 🟢 Concluído (2026-06-28); suíte atual em 274 testes verdes; cobertura 73% na última medição (era 76%/289 antes da integração do upstream) |
| 3 | Revalidar isolamento da suíte com as migrações Alembic | ▪ Média | 🔴 Pendente |
| 4 | Estratégia para divergência SQLite (teste) × MySQL (prod) | ▪ Média | 🟢 Decidido → [Plano MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md) (teste = MySQL) |
| 5 | Dívida: `datetime.utcnow()` deprecado em `app/__init__.py` | ▫ Baixa | 🔴 Pendente |
| 6 | Smoke test legado do Entra ID (migração para pytest) | ▫ Baixa | ⚪ Encerrado (2026-06-29) — testes de Entra ID removidos na integração do upstream (módulo reescrito) |
| 7 | Skill de scaffold de testes | ▫ Futuro | ⚪ Adiado (condicional) |
| 8 | `db_session` não isolava (bind ignorado pelo FSQLA) — revisões R1/X1 | 🔺 Alta | ✅ Corrigido (2026-06-27, revisão X1) |
| 9 | Limpeza frágil do SQLite temporário (revisão R2) | ▪ Média | ✅ Resolvido — SQLite removido (E6); não há mais arquivo temporário |
| 10 | Rotas órfãs `/admin/dashboard` e `/admin/audit-log` (templates ausentes) | ▪ Média | 🔴 Pendente |
| 11 | Generalizar o fuso GMT-3 na camada do ORM (naive/aware) | ▪ Média | 🔴 Pendente |

---

## 1. Gate de CI

**Prioridade:** 🔺 Alta · **Status:** 🔴 Pendente

**Por quê:** o workflow `.github/workflows/main_somasgt.yml` hoje faz **deploy
automático para o Azure a cada push na `main` sem rodar nenhum teste** (é o único
workflow, e só dispara em `push` na `main` — push em `develop` **não aciona nada**).
Sem um gate, qualquer padrão de testes é opcional e a suíte não impede regressões.
Este é o mecanismo que realmente impõe consistência num time pequeno.

**Restrições concretas de implementação (verificadas em 2026-06-29):**

- A suíte é **100% MySQL** — o `conftest.py` resolve `DATABASE_URL`/`TEST_DATABASE_URL`
  para `estoque_test` no import. O job de CI precisa de um **service container MySQL**
  (ou MySQL gerenciado no runner), criar o banco `estoque_test` e exportar
  `TEST_DATABASE_URL` antes de `pytest`. Sem isso o import da app falha na coleta.
- Fixar a **versão do Python do job em 3.14** (= local e deploy, já alinhados — ver
  [P5 ✅ em PRONTIDAO_PRODUCAO.md](../infraestrutura/PRONTIDAO_PRODUCAO.md)); o job de CI
  apenas herda essa versão única.

**Checklist:**

- [ ] Adicionar job de CI (push/PR em `develop` e `main`) com **service container MySQL**,
      que instala `requirements-dev.txt`, cria `estoque_test` e roda `pytest`.
- [ ] Fazer o job **bloquear** o merge/deploy quando os testes falharem.
- [ ] Rodar `pytest` **antes** do passo de deploy no `main_somasgt.yml` (ou em
      workflow separado exigido como status check obrigatório na branch protegida).
- [ ] Fixar a versão do Python do job em **3.14** (= local e deploy; P5 já resolvido).
- [ ] Documentar no [README de testes](README.md) que o CI é obrigatório.

---

## 2. Cobertura das rotas de maior risco

**Prioridade:** 🔺 Alta · **Status:** 🟢 Concluído (2026-06-28)

**Por quê:** com cobertura quase zero, o risco real era **regressão não detectada**
nos fluxos sensíveis. A cobertura subiu de **22% → 76%** (289 testes) nesta branch.

**Checklist (ordenado por risco):**

- [x] **Bloqueio por força bruta:** 5 tentativas falhas → bloqueio de 15 min
      (`User.pode_tentar_login`, `registrar_login_falho`). Os testes expuseram e
      levaram à correção do bug naive/aware (ver Histórico). `tests/test_models.py`,
      `tests/test_auth_routes.py`.
- [x] **RBAC:** `@require_role` barra usuário comum em rota admin (403) e libera
      admin; helpers de permissão testados. `tests/test_decorators.py`,
      `tests/test_api.py`, `tests/test_admin.py`.
- [x] **Geração do Termo de Entrega (PDF):** CLT e PJ, termo e aditivo, com e sem
      equipamentos e com laudo fotográfico. `tests/test_termo_service.py`.
- [x] **Estoque:** criar produto, entrada/saída e relatórios atualizam o saldo.
      `tests/test_estoque_service.py`, `tests/test_api.py`.
- [x] **API JSON:** CRUD de produtos/usuários/chamadas e validações de erro.
      `tests/test_api.py`.

**Fixtures auxiliares adicionadas ao `conftest.py`:** `criar_usuario` (factory),
`usuario_comum` e `user_client` (cliente logado como usuário comum) — use-as para
testar RBAC e fluxos de não-admin.

> Cobertura por área e linhas faltantes: `pytest --cov=app --cov-report=term-missing`.
> Próximo passo natural: o **gate de CI** (item #1) para travar regressões.

---

## 3. Revalidar isolamento da suíte com as migrações Alembic

**Prioridade:** ▪ Média · **Status:** 🔴 Pendente

**Por quê:** `init_database()` aplica as migrações Alembic na inicialização — já
existem **8 revisões** em `migrations/versions/`, complementadas por `db.create_all()`
e `_ensure_schema_columns()`. O isolamento por transação externa precisa ser
confirmado verde contra esse caminho de boot real (e não contra um `create_all()`
isolado).

**Checklist:**

- [ ] Ao criar a 1ª migração, rodar a suíte e confirmar que continua verde.
- [ ] Se quebrar, decidir entre: (a) aplicar migrações no banco de teste, ou
      (b) forçar `create_all()` em modo de teste.
- [ ] Atualizar a seção "padrão" do [README de testes](README.md) com a decisão.

---

## 4. Divergência SQLite (teste) × MySQL (produção)

**Prioridade:** ▪ Média · **Status:** 🟢 Resolvido — teste = MySQL

**Resolução:** a divergência deixou de existir com a padronização MySQL (Plano
**E6**): a suíte roda no banco `estoque_test` do container, **mesmo dialeto de
produção**. Não há mais SQLite. Resta apenas o gate de CI (item #1) rodando `pytest`
contra esse MySQL. Ver [Plano de Padronização MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md).

---

## 5. Dívida técnica: `datetime.utcnow()` deprecado

**Prioridade:** ▫ Baixa · **Status:** 🔴 Pendente

**Por quê:** a suíte emite `DeprecationWarning` vindos de `app/__init__.py`
(linhas ~74, ~84 e ~117) por uso de `datetime.utcnow()`, removido em versões futuras
do Python. Não quebra os testes hoje, mas é dívida visível.

**Checklist:**

- [ ] Trocar `datetime.utcnow()` por `datetime.now(datetime.UTC)` onde aplicável.
- [ ] Revisar outros usos no projeto (modelos usam fuso GMT-3).

---

## 6. Smoke test legado do Entra ID — encerrado

**Prioridade:** ▫ Baixa · **Status:** ⚪ Encerrado (2026-06-29)

**Desfecho:** a integração do upstream reescreveu o módulo Entra ID e os testes
antigos (que cobriam a API anterior) foram **removidos** junto do smoke legado
`tests/test_entra_id.py`/`.bat`. Não há mais `collect_ignore` no `conftest.py`. A
cobertura de testes para o Entra ID **reescrito** fica como pendência futura.

---

## 7. Skill de scaffold de testes

**Prioridade:** ▫ Futuro · **Status:** ⚪ Adiado (condicional)

**Por quê:** o conselho concluiu que construir uma Skill agora é prematuro —
cristalizaria suposições antes do padrão estar exercitado. **Reavaliar somente
quando** houver ~30 testes e o atrito de criar testes for medido (não imaginado).
Nesse momento, a Skill poderá reutilizar o próprio `conftest.py` como template.

**Gatilho para reativar:** suíte estável com ~30 testes + repetição perceptível na
criação de novos arquivos de teste.

---

## 8. `db_session` não isolava de verdade (revisões R1/X1)

**Prioridade:** 🔺 Alta · **Status:** ✅ Corrigido (2026-06-27, revisão X1) · **Origem:** [Revisões R1/X1](REVISAO_CODIGO.md)

**Diagnóstico corrigido:** a revisão `high` (R1) supôs `StatementError` por *bind*
global em conexão fechada. A reprodução empírica na revisão `xhigh` mostrou que
`_db.session.configure(bind=...)` é **ignorado** pelo Flask-SQLAlchemy 3.x (seu
`get_bind` resolve o engine padrão por `engines[None]` e não consulta o *bind* da
sessão). O efeito real era **isolamento inexistente**: os `commit()` dos testes iam
direto ao SQLite e vazavam entre testes. A suíte só passava porque nenhum smoke test
dependia do isolamento.

**Correção aplicada:** o `db_session` passou a usar a receita oficial do
Flask-SQLAlchemy 3.1 (*join an external transaction*): substitui cada engine por uma
conexão com transação aberta no dicionário `engines` e a restaura no teardown — assim
todo o trabalho da sessão (inclusive commits, que viram savepoints) é desfeito pelo
rollback final.

**Feito:**

- [x] Abordagem (b): vincular a sessão por-teste sem reconfigurar o factory global de
      forma persistente.
- [x] Sonda de isolamento (escreve em um teste, confirma ausência no seguinte) —
      validada verde após a correção.

> A correção é agnóstica de dialeto e continua válida quando a suíte migrar para
> MySQL. Considerar promover a sonda a teste permanente da própria base de testes.

---

## 9. Limpeza frágil do SQLite temporário (revisão R2)

**Prioridade:** ▪ Média · **Status:** ✅ Resolvido (2026-06-27) · **Origem:** [Revisão R2](REVISAO_CODIGO.md#achados)

**Resolução:** com a remoção do SQLite (Plano MySQL **E6**), os testes deixaram de
criar arquivo temporário — passam a usar o banco `estoque_test` no container MySQL.
O problema original (vazamento em `/tmp`, `PermissionError` por lock no Windows)
deixou de existir. Não há mais `tempfile`/`os.remove` no `conftest.py`.

---

## 10. Rotas órfãs `/admin/dashboard` e `/admin/audit-log`

**Prioridade:** ▪ Média · **Status:** 🔴 Pendente · **Origem:** escrita dos testes (2026-06-28)

**Por quê:** ambas as views (`dashboard`, `audit_log` em `app/routes/admin.py`)
renderizam templates que **não existem** (`admin/dashboard.html`,
`admin/audit_log.html`) e **nenhum link** aponta para elas — o dashboard real é
servido por `main.py:/admin`. Acessá-las executa a query e então levanta
`TemplateNotFound` (erro 500). São código morto que aparenta funcionar.

**Checklist:**

- [ ] Decidir: **remover** as duas rotas (e suas funções) ou **criar** os templates.
- [ ] Os testes `test_dashboard_rota_orfa_sem_template` /
      `test_audit_log_rota_orfa_sem_template` (`tests/test_admin.py`) documentam o
      estado atual — atualizá-los conforme a decisão.

---

## 11. Generalizar o fuso GMT-3 na camada do ORM (naive/aware)

**Prioridade:** ▪ Média · **Status:** 🔴 Pendente · **Origem:** revisão `xhigh` (2026-06-28, achado de altitude)

**Por quê:** o MySQL grava `DATETIME` sem fuso; os modelos escrevem *aware*
(`now_gmt3()`) e leem *naive*, o que já causou o erro 500 no bloqueio por força
bruta. A correção atual (`_garantir_aware_gmt3` em `app/models/__init__.py`)
reanexa o fuso **por ponto de comparação** — funciona, mas só cobre `bloqueado_ate`.
As demais colunas (`ultimo_login`, `data_assinatura`, `data_criacao`, etc.)
levantarão o mesmo `TypeError` assim que forem comparadas com um *aware* — inclusive
a feature planejada em [CHAMADO_AUTOMATICO_FORCA_BRUTA](../seguranca/CHAMADO_AUTOMATICO_FORCA_BRUTA.md).

**Checklist:**

- [ ] Avaliar um `TypeDecorator` (ou `DateTime(timezone=True)` / normalização na
      escrita) que torne leitura e escrita simétricas para **todas** as colunas.
- [ ] Remover os usos pontuais de `_garantir_aware_gmt3` quando a base ficar consistente.
- [ ] Revisar comparações de datetime feitas no nível do SQL em `app/routes/api.py`
      (ex.: filtros por data) quanto a *offset* vindo do cliente.

---

## Histórico (itens concluídos)

- 🟢 **2026-06-29** — Integração do commit do upstream (`YanWaltrick/ESTOQUE-1.0`),
  que **reescreveu o módulo Entra ID** (`app/auth/entra_id.py` e
  `app/routes/entra_auth.py` — API e rotas diferentes) e adicionou a rota
  `/admin-login`. Os testes de Entra ID do fork (`tests/test_entra.py`, 23 testes)
  cobriam a API **antiga** e tornaram-se incompatíveis; foram **removidos** junto
  do smoke legado `tests/test_entra_id.py`/`.bat` (item #6 encerrado). A suíte
  passou de 289 para **266 testes** (todos verdes). Cobertura de testes para o
  Entra ID reescrito fica como pendência futura (ver item #6).
- 🟢 **2026-06-28** — Revisão `xhigh` da PR de cobertura: 13 achados corrigidos na
  branch `fix/correcoes-revisao-cobertura` (401 JSON para API não autenticada;
  `is_active` sem commit colateral; testes vacuous fortalecidos; dedup de fixtures).
  Achados de profundidade registrados como itens #10 e #11. Detalhe em
  [REVISAO_CODIGO.md](REVISAO_CODIGO.md#2026-06-28--revisão-xhigh-da-pr-de-cobertura-3--correções-aplicadas).
- 🟢 **2026-06-28** — Cobertura de testes de 22% → **76%** (289 testes) na branch
  `feature/aumentar-cobertura-testes`. Novos arquivos: `test_models`,
  `test_security`, `test_decorators`, `test_logger`, `test_estoque_service`,
  `test_notification_service`, `test_termo_service`, `test_api`, `test_admin`,
  `test_auth_routes`, `test_main_routes`, `test_entra`. Fixtures `criar_usuario`/
  `usuario_comum`/`user_client` no `conftest.py`. **Bugs corrigidos** descobertos
  pelos testes: (a) comparação naive/aware no bloqueio por força bruta de `User`
  (erro 500 no login de conta bloqueada); (b) status HTTP em `criar_usuario_api`
  (`jsonify({...}, 400)` → `jsonify({...}), 400`). **Achado documentado:** rotas
  órfãs (item #10).
- 🟢 **2026-06-27** — Revisão `xhigh` com correções aplicadas: #8 (`db_session` agora
  isola de verdade) e #6 mitigado (`collect_ignore` do smoke legado). Ver
  [REVISAO_CODIGO.md](REVISAO_CODIGO.md#2026-06-27--revisão-xhigh-do-fork--correções-aplicadas).
- 🟢 **2026-06-27** — Configuração inicial do `pytest`, `conftest.py` com fixtures
  base (app/banco isolado/`client`/`auth_client`) e 4 testes de fumaça do login.
  Correção do `CLAUDE.md` (afirmava não haver testes). Branch
  `feature/implementacao-testes`.

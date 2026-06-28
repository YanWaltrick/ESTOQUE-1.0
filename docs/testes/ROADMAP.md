# Roadmap de Testes — Pendências e Próximos Passos

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> Atualize o status e os checklists **na mesma tarefa** em que o trabalho for feito.
>
> **Última atualização:** 2026-06-27 — revisão `xhigh`: item #8 corrigido, #6 mitigado

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
| 2 | Cobertura das rotas de maior risco | 🔺 Alta | 🔴 Pendente |
| 3 | Revalidar isolamento com a 1ª migração Alembic | ▪ Média | 🔴 Pendente |
| 4 | Estratégia para divergência SQLite (teste) × MySQL (prod) | ▪ Média | 🟢 Decidido → [Plano MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md) (teste = MySQL) |
| 5 | Dívida: `datetime.utcnow()` deprecado em `app/__init__.py` | ▫ Baixa | 🔴 Pendente |
| 6 | Migrar smoke test legado do Entra ID para pytest | ▫ Baixa | 🟡 Mitigado (`collect_ignore`) — migração pendente |
| 7 | Skill de scaffold de testes | ▫ Futuro | ⚪ Adiado (condicional) |
| 8 | `db_session` não isolava (bind ignorado pelo FSQLA) — revisões R1/X1 | 🔺 Alta | ✅ Corrigido (2026-06-27, revisão X1) |
| 9 | Limpeza frágil do SQLite temporário (revisão R2) | ▪ Média | ✅ Resolvido — SQLite removido (E6); não há mais arquivo temporário |

---

## 1. Gate de CI

**Prioridade:** 🔺 Alta · **Status:** 🔴 Pendente

**Por quê:** o workflow `.github/workflows/main_somasgt.yml` hoje faz **deploy
automático para o Azure a cada push na `main` sem rodar nenhum teste**. Sem um gate,
qualquer padrão de testes é opcional e a suíte não impede regressões. Este é o
mecanismo que realmente impõe consistência num time pequeno.

**Checklist:**

- [ ] Adicionar job de CI que instala `requirements-dev.txt` e roda `pytest`.
- [ ] Fazer o job **bloquear** o merge/deploy quando os testes falharem.
- [ ] Rodar `pytest` **antes** do passo de deploy no `main_somasgt.yml` (ou em
      workflow separado exigido como status check).
- [ ] Documentar no [README de testes](README.md) que o CI é obrigatório.

---

## 2. Cobertura das rotas de maior risco

**Prioridade:** 🔺 Alta · **Status:** 🔴 Pendente

**Por quê:** com cobertura quase zero, o risco real é **regressão não detectada** nos
fluxos sensíveis — não a uniformidade de formato dos testes. Priorizar por
criticidade, não por facilidade.

**Checklist (ordenado por risco):**

- [ ] **Bloqueio por força bruta:** 5 tentativas falhas → bloqueio de 15 min
      (`User.pode_tentar_login`, `registrar_login_falho`).
- [ ] **RBAC:** decorador `@require_role` barra usuário comum em rota de admin
      (403) e libera admin; `@require_permission` idem.
- [ ] **Geração do Termo de Entrega (PDF):** `app/services/termo_service.py` gera
      PDF para CLT e PJ sem erro.
- [ ] **Estoque:** criar produto e registrar movimentação atualiza o saldo.
- [ ] **API JSON:** ao menos um endpoint de `api_bp` retorna o JSON esperado.

> Use as fixtures `auth_client` e `db_session` do `conftest.py`. Para testar usuário
> comum, criar uma fixture/auxiliar de usuário `role='usuario'` quando necessário.

---

## 3. Revalidar isolamento com a primeira migração Alembic

**Prioridade:** ▪ Média · **Status:** 🔴 Pendente

**Por quê:** `init_database()` aplica migrações Alembic na inicialização quando
existem revisões. Hoje **não há nenhuma**, então o conftest cai em `db.create_all()`
e tudo funciona. Assim que a primeira migração for gerada, o caminho de inicialização
muda e pode conflitar com o SQLite temporário / transação de teste.

**Checklist:**

- [ ] Ao criar a 1ª migração, rodar a suíte e confirmar que continua verde.
- [ ] Se quebrar, decidir entre: (a) aplicar migrações no banco de teste, ou
      (b) forçar `create_all()` em modo de teste.
- [ ] Atualizar a seção "padrão" do [README de testes](README.md) com a decisão.

---

## 4. Divergência SQLite (teste) × MySQL (produção)

**Prioridade:** ▪ Média · **Status:** 🔴 Pendente

**Por quê:** os testes rodam em SQLite, mas produção é MySQL. Diferenças de tipos,
de `LargeBinary` (coluna de `DocumentoArquivo`) e de comportamento podem fazer um
teste passar localmente e o bug aparecer só no Azure.

**Checklist:**

- [ ] Mapear pontos sensíveis a dialeto (tipos binários, `DATETIME`, defaults).
- [ ] Avaliar um job de CI opcional rodando a suíte contra um MySQL de serviço.
- [ ] Documentar a decisão (rodar só SQLite vs. matriz SQLite+MySQL).

---

## 5. Dívida técnica: `datetime.utcnow()` deprecado

**Prioridade:** ▫ Baixa · **Status:** 🔴 Pendente

**Por quê:** a suíte emite `DeprecationWarning` vindos de `app/__init__.py`
(linhas ~51 e ~94) por uso de `datetime.utcnow()`, removido em versões futuras do
Python. Não quebra os testes hoje, mas é dívida visível.

**Checklist:**

- [ ] Trocar `datetime.utcnow()` por `datetime.now(datetime.UTC)` onde aplicável.
- [ ] Revisar outros usos no projeto (modelos usam fuso GMT-3).

---

## 6. Migrar smoke test legado do Entra ID para pytest

**Prioridade:** ▫ Baixa · **Status:** 🟡 Mitigado (`collect_ignore`) — migração pendente

**Por quê:** `tests/test_entra_id.py` valida imports via `print`/`exit`, fora do
padrão pytest. Funciona, mas não integra à suíte nem ao relatório de cobertura.

**Mitigação aplicada (revisão X2):** o pytest importava esse arquivo na coleta (casa
com `python_files = test_*.py`), executando `create_app()` e podendo chamar `exit(1)`.
Adicionado `collect_ignore = ["test_entra_id.py"]` no `conftest.py` para excluí-lo da
coleta sem perder a execução standalone. A migração completa abaixo segue pendente.

**Checklist:**

- [x] Impedir que o pytest importe/rode o script legado na coleta (`collect_ignore`).
- [ ] Reescrever as 4 verificações como testes `pytest` (imports, blueprint,
      app factory).
- [ ] Remover o script `.py`/`.bat` legado após a migração (e o `collect_ignore`).

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

## Histórico (itens concluídos)

- 🟢 **2026-06-27** — Revisão `xhigh` com correções aplicadas: #8 (`db_session` agora
  isola de verdade) e #6 mitigado (`collect_ignore` do smoke legado). Ver
  [REVISAO_CODIGO.md](REVISAO_CODIGO.md#2026-06-27--revisão-xhigh-do-fork--correções-aplicadas).
- 🟢 **2026-06-27** — Configuração inicial do `pytest`, `conftest.py` com fixtures
  base (app/banco isolado/`client`/`auth_client`) e 4 testes de fumaça do login.
  Correção do `CLAUDE.md` (afirmava não haver testes). Branch
  `feature/implementacao-testes`.

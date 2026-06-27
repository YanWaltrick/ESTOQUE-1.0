# Roadmap de Testes — Pendências e Próximos Passos

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> Atualize o status e os checklists **na mesma tarefa** em que o trabalho for feito.
>
> **Última atualização:** 2026-06-27 — branch `feature/implementacao-testes`

Origem da maioria destes itens: veredito do Conselho de LLMs sobre a estratégia de
testes (ver `## A Recomendação` / `## Pontos Cegos`). Os itens #8 e #9 vêm da
[Revisão de Código de 2026-06-27](REVISAO_CODIGO.md). O raciocínio do "porquê" está
preservado em cada item.

> ⚠️ **Direção do banco de teste decidida (2026-06-27):** a suíte vai migrar de
> SQLite para **MySQL** (mesmo dialeto de produção). Ver
> [Plano de Padronização MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md) —
> planejado, **ainda não implementado**. Os itens #8 e #9 abaixo deixam de ser
> corrigidos no SQLite e serão **resolvidos pela migração** (etapas E2/E3 do plano).

---

## Visão geral

| # | Item | Prioridade | Status |
|---|------|-----------|--------|
| 1 | Gate de CI rodando `pytest` | 🔺 Alta | 🔴 Pendente |
| 2 | Cobertura das rotas de maior risco | 🔺 Alta | 🔴 Pendente |
| 3 | Revalidar isolamento com a 1ª migração Alembic | ▪ Média | 🔴 Pendente |
| 4 | Estratégia para divergência SQLite (teste) × MySQL (prod) | ▪ Média | 🟢 Decidido → [Plano MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md) (teste = MySQL) |
| 5 | Dívida: `datetime.utcnow()` deprecado em `app/__init__.py` | ▫ Baixa | 🔴 Pendente |
| 6 | Migrar smoke test legado do Entra ID para pytest | ▫ Baixa | 🔴 Pendente |
| 7 | Skill de scaffold de testes | ▫ Futuro | ⚪ Adiado (condicional) |
| 8 | `db_session` deixa bind global em conexão fechada (revisão R1) | 🔺 Alta | ⚪ Absorvido pelo [Plano MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md) (E2/E3) |
| 9 | Limpeza frágil do SQLite temporário (revisão R2) | ▪ Média | ⚪ Absorvido — SQLite será removido (Plano MySQL E6) |

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

**Prioridade:** ▫ Baixa · **Status:** 🔴 Pendente

**Por quê:** `tests/test_entra_id.py` valida imports via `print`/`exit`, fora do
padrão pytest. Funciona, mas não integra à suíte nem ao relatório de cobertura.

**Checklist:**

- [ ] Reescrever as 4 verificações como testes `pytest` (imports, blueprint,
      app factory).
- [ ] Remover o script `.py`/`.bat` legado após a migração.

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

## 8. `db_session` deixa bind global em conexão fechada (revisão R1)

**Prioridade:** 🔺 Alta · **Status:** 🔴 Pendente · **Origem:** [Revisão R1](REVISAO_CODIGO.md#achados)

**Por quê:** o fixture `db_session` reconfigura o sessionmaker compartilhado (escopo
de sessão) com `_db.session.configure(bind=connection, ...)`, mas no teardown a
conexão é fechada e o bind nunca é resetado. Qualquer teste futuro que use
`client`/`auth_client`, toque o banco e **não** dependa de `db_session`, rodando
após um teste com `db_session`, abrirá sessão presa à conexão fechada →
`StatementError`. A suíte atual só escapa pela ordem dos testes. Como o
`conftest.py` é o padrão a ser copiado, o problema se propaga.

**Checklist (escolher uma abordagem):**

- [ ] (a) Tornar **todos** os testes dependentes de `db_session`, ou
- [ ] (b) Vincular a sessão por-teste sem mutar o factory global (padrão
      documentado do Flask-SQLAlchemy 3.1), ou
- [ ] (c) Resetar o bind no teardown (`_db.session.configure(bind=None)` /
      re-vincular ao engine) além do `remove()`.
- [ ] Adicionar um teste que escreve no banco e confirma rollback (valida o
      isolamento, hoje não exercitado).

---

## 9. Limpeza frágil do SQLite temporário (revisão R2)

**Prioridade:** ▪ Média · **Status:** 🔴 Pendente · **Origem:** [Revisão R2](REVISAO_CODIGO.md#achados)

**Por quê:** o arquivo de banco é criado no import do módulo; se a coleção falhar
antes da fixture `app`, vaza em `/tmp`. Além disso, o engine não é descartado antes
do `os.remove`, o que no Windows (suportado — há `tests/test_entra_id.bat`) causa
`PermissionError` por lock de conexões pooled.

**Checklist:**

- [ ] Descartar o engine antes de remover o arquivo (`_db.engine.dispose()` no
      teardown).
- [ ] Proteger o `os.remove` para não mascarar erro / lidar com Windows.
- [ ] Avaliar `tmp_path_factory` do pytest para o pytest gerenciar o ciclo de vida
      do arquivo.

---

## Histórico (itens concluídos)

- 🟢 **2026-06-27** — Configuração inicial do `pytest`, `conftest.py` com fixtures
  base (app/banco isolado/`client`/`auth_client`) e 4 testes de fumaça do login.
  Correção do `CLAUDE.md` (afirmava não haver testes). Branch
  `feature/implementacao-testes`.

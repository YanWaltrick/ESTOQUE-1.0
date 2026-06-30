# Prontidão para Produção (Azure App Service) — Bloqueios de Go-Live

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> Atualize status e checklists **na mesma tarefa** em que o trabalho for feito.
>
> **Última atualização:** 2026-06-29 — P2 revisado: `static/uploads/` deixou de ser
> versionado (rede de proteção do git removida) e documentos ganharam fallback ao banco
> também no admin; persistência de avatares/anexos/fotos segue pendente. Antes: criação a
> partir do veredito do Conselho.

**Origem:** veredito do [Conselho de LLMs sobre a escolha de stack (2026-06-29)](../adr/0001-manter-flask-como-stack.md).
O conselho foi unânime: **a stack (Flask) está validada** — o risco real é
**operacional**. "Compila na Azure" **≠** "pronto para produção". Este documento
rastreia os bloqueios entre o estado atual e um go-live seguro.

> **Premissa:** a decisão de manter Flask está registrada na
> [ADR 0001](../adr/0001-manter-flask-como-stack.md). Aqui ficam apenas as
> **pendências de prontidão**, não a discussão de framework.

---

## Visão geral

| # | Bloqueio | Prioridade | Status | Dono / referência |
|---|----------|-----------|--------|-------------------|
| P1 | Credencial admin default (`admin`/`admin`) + senha em log | 🔺 Alta | 🔴 Pendente | **este doc** |
| P2 | Uploads gravados em disco efêmero do App Service | 🔺 Alta | 🟡 Parcial | **este doc** + [custo/latência A4](PLANO_INVESTIGACAO_CUSTO_LATENCIA.md) |
| P3 | Migrations/`ALTER` no boot com múltiplos workers | 🔺 Alta | 🔴 Pendente | ↪ [custo/latência A1](PLANO_INVESTIGACAO_CUSTO_LATENCIA.md) |
| P4 | Secrets, cookie seguro e startup command explícito | 🔺 Alta | 🔴 Pendente | **este doc** |
| P5 | Parity de Python: 3.13 local × 3.14 no build | ▪ Média | 🔴 Pendente | **este doc** |
| P6 | Observabilidade (health check, App Insights, alertas) | ▪ Média | 🔴 Pendente | **este doc** |
| P7 | Gate de testes no CI + staging/rollback | 🔺 Alta | 🟡 Parcial | ↪ [testes/ROADMAP #1](../testes/ROADMAP.md) |
| P8 | LGPD dos documentos pessoais (CLT/PJ) | ▪ Média | 🔴 Pendente | ↪ [custo/latência §4.3](PLANO_INVESTIGACAO_CUSTO_LATENCIA.md) |
| P9 | Backup com **restore testado** (RTO/RPO) | ▪ Média | 🔴 Pendente | **este doc** |
| P10 | Integridade dos dados de estoque (constraints/transações) | ▪ Média | 🔴 Pendente | **este doc** |
| — | Estado de bloqueio de login persiste no banco | — | ✅ Verificado | — |

> **A única coisa a fazer primeiro:** **P1.** É a falha mais barata de corrigir e a
> mais cara de ignorar.

---

## P1. Credencial admin default (`admin`/`admin`) + senha em log

**Prioridade:** 🔺 Alta (segurança crítica) · **Status:** 🔴 Pendente

**Por quê:** `init_database()` cria automaticamente um usuário `admin` com senha
`admin` (`app/__init__.py:273`) e **imprime a credencial em texto claro no log**
(`app/__init__.py:276`: *"Usuario admin criado (login: admin / senha: admin)"*).
Pior: quando o hash não bate, a senha é **redefinida para `admin`** e isso também é
logado (`app/__init__.py:286,288,290,304`). Um sistema corporativo exposto à internet
com credencial pública conhecida cai no primeiro scan de rede.

**Checklist:**

- [ ] Remover o `print` da senha (P1 é também vazamento via log).
- [ ] Não criar mais admin com senha fixa: gerar senha aleatória forte e/ou exigir
      troca obrigatória no primeiro login; ou provisionar o admin via secret/variável
      de ambiente (nunca hardcoded).
- [ ] Remover o caminho que **redefine** a senha para `admin` em mismatch de hash.
- [ ] Confirmar que nenhum ambiente vivo ainda tem a senha `admin` ativa.

---

## P2. Uploads gravados em disco efêmero do App Service

**Prioridade:** 🔺 Alta · **Status:** 🟡 Parcial (documentos com fallback ao banco; avatares/anexos/fotos ainda só no disco)

**Por quê:** avatares, fotos e anexos são salvos no filesystem local em
`static/uploads/` (`auth.py:370`, `api.py:660`/`915`, `admin.py:201`/`385`/`438`/`658`,
`main.py:128`). O disco do App Service é **efêmero** — some a cada deploy, restart ou
scale-out. Hoje há **duas estratégias simultâneas** de armazenamento (disco **e** BLOB
no banco via `DocumentoArquivo`), o que não é redundância: é indecisão arquitetural —
metade dos arquivos sobrevive, metade evapora.

> **Mudança de contexto (2026-06-29):** até então o `static/uploads/` era **versionado no
> git**, e o deploy (`path: .` no `main_somasgt.yml`) reentregava esses arquivos ao App
> Service a cada release — o que **mascarava** o problema (o disco "se reenchia" sozinho).
> Esse versionamento foi **removido** (inchava o repo e expunha dados pessoais — ver P8).
> A partir daqui o disco **não se reenche** no deploy, o que torna P2 **acionável antes do
> próximo deploy na `main`**, não mais uma melhoria adiável.

**Estado por tipo de arquivo:**

| Tipo | Persistência fora do disco | Leitura resiliente |
|------|----------------------------|--------------------|
| Documentos (`documentos/`, inclui termos PDF) | `DocumentoArquivo` (banco) — **se** migrados | ✅ usuário (`main.py`) **e** admin (`admin.py`) com fallback ao banco |
| Avatares (`avatars/`) | ❌ nenhuma | ❌ só disco |
| Anexos de chamados (`chamadas/`) | ❌ nenhuma | ❌ só disco |
| Fotos de termos (`termos/`) | ❌ nenhuma | ❌ só disco |

**Checklist:**

- [ ] **Antes do próximo deploy na `main`:** rodar `python scripts/migrate_docs_to_db.py`
      **no ambiente de produção** — sem isso o fallback ao banco não tem o que servir e os
      documentos hoje no disco somem no deploy.
- [ ] **Confirmar a premissa do disco efêmero:** validar empiricamente se o App Service
      persiste o filesystem entre deploys (subir um arquivo, dar deploy, ver se sobrevive).
      Se **não** persistir, os itens abaixo deixam de ser melhoria e viram bloqueio de go-live.
- [ ] Definir **uma** fonte de verdade para arquivos: **Azure Blob Storage**
      (recomendado) ou coluna no MySQL — disco local **não** é opção em App Service.
- [ ] Levar **avatares, anexos de chamados e fotos de termos** para a fonte escolhida —
      hoje **não têm** nenhuma cópia fora do disco; migrar os respectivos pontos de `save()`.
- [ ] Conciliar com a decisão de mover BLOBs do banco
      ([custo/latência A4](PLANO_INVESTIGACAO_CUSTO_LATENCIA.md)) — idealmente o mesmo
      destino para tudo.

**Feito:**

- [x] (2026-06-29) Documentos do admin passam a cair para o banco quando o disco está
      vazio (`admin.py`: `visualizar_documento`/`download_documento`), espelhando a rota
      do usuário (`main.py`) — leitura resiliente de documentos em ambas as telas.

> Relacionado: a arquitetura de armazenamento de documentos é decidida em conjunto com
> o [Plano de Padronização MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md) e a
> [Investigação de Custo & Latência](PLANO_INVESTIGACAO_CUSTO_LATENCIA.md).

---

## P3. Migrations/`ALTER` no boot com múltiplos workers

**Prioridade:** 🔺 Alta · **Status:** 🔴 Pendente · **Dono:** [custo/latência A1](PLANO_INVESTIGACAO_CUSTO_LATENCIA.md)

**Por quê:** `init_database()` roda `upgrade(revision='head')` (`app/__init__.py:245`)
+ `db.create_all()` (`:255`) + `_ensure_schema_columns()` (`:268`) **a cada
inicialização**. Com gunicorn subindo vários workers em paralelo no App Service, todos
disparam migração e `ALTER TABLE` ao mesmo tempo contra o mesmo MySQL — DDL não é
transacional em MySQL: **race de schema**, lock de tabela e cold start lento. Ter
migration formal **e** `create_all()` **e** patch manual de colunas é sinal de que
ninguém confia nas migrations.

**Ação:** tirar migrations/`ALTER` do startup e rodá-los como **passo de deploy**
(`flask db upgrade` no GitHub Actions, antes do release), deixando a aplicação apenas
subir. **Item já rastreado como A1** em
[custo/latência](PLANO_INVESTIGACAO_CUSTO_LATENCIA.md#3-plano-de-ação-priorizado-após-diagnóstico);
não duplicar aqui — atualizar lá.

---

## P4. Secrets, cookie seguro e startup command explícito

**Prioridade:** 🔺 Alta · **Status:** 🔴 Pendente

**Por quê:** configuração de produção que não pode depender de default.

**Checklist:**

- [ ] **Secrets** (`SECRET_KEY`, `DATABASE_URL`, secrets do Entra ID) em Application
      Settings / **Azure Key Vault** — nunca no repositório.
- [ ] `SESSION_COOKIE_SECURE=True` (e `SameSite=Lax`) em produção com HTTPS.
- [ ] **Startup command explícito** no App Service, com timeout folgado para uploads
      grandes (BLOB no banco estoura o default de 30 s):
      `gunicorn --bind=0.0.0.0:8000 --workers=4 --timeout=120 wsgi:app`.
- [ ] Validar `max_allowed_packet` do MySQL Azure compatível com o tamanho dos BLOBs.

---

## P5. Parity de Python: 3.13 local × 3.14 no build

**Prioridade:** ▪ Média · **Status:** 🔴 Pendente

**Por quê:** `mise.toml` fixa **Python 3.13**; o workflow
`.github/workflows/main_somasgt.yml` builda em **3.14** (`setup-python` com
`python-version: '3.14'`). Testa-se num runtime e entrega-se em outro — divergências
de comportamento de ReportLab/PyMySQL/MSAL só apareceriam em produção.

**Checklist:**

- [ ] Alinhar a versão: subir o `mise.toml` para 3.14 **ou** travar o build em 3.13.
- [ ] Garantir que a suíte roda na **mesma** versão usada no deploy.

---

## P6. Observabilidade (health check, App Insights, alertas)

**Prioridade:** ▪ Média · **Status:** 🔴 Pendente

**Por quê:** sem health check, telemetria e alertas, "estar em produção" é voar
cego — não há como saber que a aplicação quebrou. Achado da rodada de revisão por
pares do conselho (nenhum conselheiro individual havia citado).

**Checklist:**

- [ ] Endpoint de **health check** leve (sem tocar no banco a cada ping pesado).
- [ ] **Application Insights** (ou equivalente) para erros e latência de request.
- [ ] **Alertas** mínimos: taxa de erro 5xx, indisponibilidade, falha de deploy.

---

## P7. Gate de testes no CI + staging/rollback

**Prioridade:** 🔺 Alta · **Status:** 🟡 Parcial · **Dono:** [testes/ROADMAP #1](../testes/ROADMAP.md)

**Por quê:** o workflow faz **deploy automático para a Azure a cada push na `main`
sem rodar testes** e **sem ambiente de homologação** — push direto em produção. O gate
de CI já é o **item #1** do [Roadmap de Testes](../testes/ROADMAP.md) (não duplicar).
Falta ainda, do ângulo de infraestrutura: **staging** e **plano de rollback**.

**Checklist (parte de infra; o gate de CI vive no roadmap de testes):**

- [ ] Avaliar slot de **staging** no App Service com swap para produção.
- [ ] Definir o procedimento de **rollback** (slot anterior / redeploy de artefato).

---

## P8. LGPD dos documentos pessoais (CLT/PJ)

**Prioridade:** ▪ Média · **Status:** 🔴 Pendente · **Ref.:** [custo/latência §4.3](PLANO_INVESTIGACAO_CUSTO_LATENCIA.md)

**Por quê:** o sistema guarda termos e documentos com **dados pessoais** de
colaboradores (Termo de Entrega CLT/PJ). Falta tratar base legal, retenção e
criptografia em repouso — ponto levantado na revisão por pares e já antecipado como
cuidado na [Investigação de Custo & Latência](PLANO_INVESTIGACAO_CUSTO_LATENCIA.md#4-cuidados-não-negociáveis-achados-da-revisão-por-pares)
ao mover arquivos para Blob Storage.

**Checklist:**

- [ ] Mapear quais documentos contêm dados pessoais e sua base legal/retenção.
- [ ] Garantir criptografia em repouso e controle de acesso (URLs assinadas se Blob).
- [ ] Conectar a decisão à escolha de armazenamento (P2).

---

## P9. Backup com restore testado (RTO/RPO)

**Prioridade:** ▪ Média · **Status:** 🔴 Pendente

**Por quê:** ponto cego pego na revisão por pares do conselho — backup que nunca foi
restaurado **não é backup**. Sem RTO/RPO definidos e sem um restore exercitado, a
recuperação só seria descoberta no pior momento. Vale tanto para o MySQL quanto para
o armazenamento de arquivos escolhido em P2.

**Checklist:**

- [ ] Definir **RTO/RPO** alvo (quanto tempo de indisponibilidade e quanta perda de
      dados são aceitáveis).
- [ ] Confirmar backup automático do MySQL Azure (retenção e point-in-time restore).
- [ ] **Executar um restore de teste** ponta a ponta — não apenas confiar que o
      backup existe.
- [ ] Incluir o armazenamento de documentos (P2) no plano de backup/restore.

---

## P10. Integridade dos dados de estoque

**Prioridade:** ▪ Média · **Status:** 🔴 Pendente

**Por quê:** o conselho (ângulo de Primeiros Princípios) apontou que **os dados** são o
que é caro de reverter — não a stack. Movimentações de estoque que "mentem" em relação
ao físico, sem garantias no nível do banco, são o risco de negócio real. A correção é
mais barata agora do que depois de meses de dados inconsistentes em produção.

**Checklist:**

- [ ] Revisar **constraints** e tipos no schema (saldo não-negativo onde aplicável,
      chaves estrangeiras, `NOT NULL`).
- [ ] Garantir que entrada/saída e atualização de saldo ocorram em **transação**
      atômica (sem janela de saldo inconsistente).
- [ ] Avaliar uma rotina de **conciliação** saldo calculado × movimentações.

> Conecta com a [Revisão de Código do banco](../banco-de-dados/REVISAO_CODIGO.md) e o
> item #11 do [testes/ROADMAP](../testes/ROADMAP.md) (fuso naive/aware nas colunas de
> data, que já causou erro 500).

---

## Verificado — sem ação

- **Bloqueio de login persiste no banco.** O estado de força bruta mora em colunas do
  modelo `User` (`tentativas_login_falhas`, `bloqueado_ate` em
  `app/models/__init__.py`), e não em memória de worker — consistente entre múltiplos
  workers do gunicorn. A preocupação do conselho ("confirmar que não está em memória")
  está satisfeita. (Pendência *correlata* sobre fuso naive/aware dessas colunas: item
  #11 do [testes/ROADMAP](../testes/ROADMAP.md).)
- **Pool de conexões.** `pool_pre_ping=True` e `pool_recycle=280`
  (`app/database.py:60-61`) já tratam conexões MySQL ociosas/derrubadas na Azure.

---

## Relação com outros documentos

- **Decisão de stack:** [ADR 0001 — Manter Flask](../adr/0001-manter-flask-como-stack.md).
- **Migrations no boot e BLOBs:** [Investigação de Custo & Latência](PLANO_INVESTIGACAO_CUSTO_LATENCIA.md)
  (A1, A4) e [Plano de Padronização MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md).
- **Gate de CI:** [Roadmap de Testes #1](../testes/ROADMAP.md).
- **Segurança:** [SECURITY.md](../SECURITY.md).

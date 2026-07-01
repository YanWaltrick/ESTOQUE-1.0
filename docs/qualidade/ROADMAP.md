# Roadmap de Qualidade de Código — Lint, Formatação e Type Checking

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> Atualize o status e os checklists **na mesma tarefa** em que o trabalho for feito.
>
> **Última atualização:** 2026-07-01 — a pendência de configuração não-versionável do Ruff
> (required status check no GitHub + `git config` local) ganhou runbook dedicado em
> [CONFIGURACAO_GIT.md](CONFIGURACAO_GIT.md), referenciado no item #2. Antes (2026-06-30):
> itens #1, #2 e #3 **implementados** — baseline do Ruff (`0.15.20`) aplicada e registrada no
> `.git-blame-ignore-revs`, triagem dos 54 avisos concluída, gate de CI de lint (`ci.yml`) em
> PR e `pre-commit`/`.editorconfig`/`.vscode`. Resta uma ação manual: marcar o job como
> *required status check* na proteção de branch. Type checking (#4) segue adiado. Antes:
> criação do roadmap a partir do veredito do Conselho de LLMs; paridade de Python (3.14)
> resolvida ([P5 ✅](../infraestrutura/PRONTIDAO_PRODUCAO.md)).

**Origem da decisão:** [ADR 0002 — Ruff para lint + formatação; type checking adiado](../adr/0002-ruff-para-lint-format-e-type-checking.md)
(veredito do Conselho de LLMs, 2026-06-30). O "porquê" de cada escolha está na ADR; aqui
mora o **plano de execução** com checklists acionáveis.

**Decisão em uma frase:** adotar **Ruff** (lint + formatação) com regras mínimas,
aplicar a baseline num commit isolado, enforçar via **gate de CI** bloqueante; **adiar**
o type checking.

---

## Visão geral

| # | Item | Prioridade | Status |
|---|------|-----------|--------|
| 0 | Paridade de Python (pré-requisito) | 🔺 Alta | ✅ Resolvido (2026-06-30) — `mise.toml` em 3.14 |
| 1 | Baseline do Ruff (config + format + `.git-blame-ignore-revs`) | 🔺 Alta | ✅ Concluído (2026-06-30) — `ruff==0.15.20`, baseline em commit isolado, triagem dos 54 avisos restantes |
| 2 | Gate de CI de lint (job dedicado, bloqueante) | 🔺 Alta | 🟡 Quase — workflow `ci.yml` criado; **falta** marcar como *required status check* (ação manual no GitHub) |
| 3 | `pre-commit` + paridade de editor (conveniência) | ▪ Média | ✅ Concluído (2026-06-30) — `.pre-commit-config.yaml`, `.editorconfig`, `.vscode/` |
| 4 | Type checking (adiado) | ▫ Futuro | ⚪ Adiado (condicional) |

> **Baseline aplicada (item #1 ✅).** O `pyproject.toml`, a baseline em commit isolado e o
> `.git-blame-ignore-revs` já existem. **Próximo passo:** **item #2** — enforçar o Ruff via
> gate de CI bloqueante em PR (o único mecanismo que realmente impede regressão de estilo).

---

## 0. Paridade de Python — pré-requisito ✅

**Prioridade:** 🔺 Alta · **Status:** ✅ Resolvido (2026-06-30)

**Por quê:** o `target-version` do Ruff e a versão do job de CI precisam casar com o que
produção roda. O `mise.toml` fixava 3.13 enquanto o build/deploy usava 3.14 (divergência
[P5](../infraestrutura/PRONTIDAO_PRODUCAO.md)). Resolvido alinhando o local para **3.14**.

**Feito:**

- [x] `mise.toml` → `python = "3.14"`.
- [x] Docs de setup atualizadas (`README.md`, `docs/ONBOARDING.md`, `CLAUDE.md`).
- [x] [P5](../infraestrutura/PRONTIDAO_PRODUCAO.md) marcado como resolvido.

---

## 1. Baseline do Ruff

**Prioridade:** 🔺 Alta · **Status:** ✅ Concluído (2026-06-30)

**Por quê:** estabelece a fundação (config única) e aplica a formatação a todo o
codebase de uma vez. Lint gradual deixa ruído eterno no diff; a baseline única encerra
isso. O primeiro `ruff format` reescreve muitos arquivos — **tem de** ser um commit
isolado + `.git-blame-ignore-revs`, senão polui o `git blame` (ponto cego pego na
revisão por pares).

**Feito:**

- [x] `requirements-dev.txt` com a **versão fixada** `ruff==0.15.20` (o patch exato vigente).
- [x] `pyproject.toml` na raiz, começando **frouxo** (regras `E`, `F`, `I`, `UP`, `B`;
      `ignore = ["E501"]`; `target-version = "py314"`; `line-length = 100`;
      `extend-exclude = ["migrations", ".venv", "antenv"]`).
- [x] Baseline (`ruff format .` + `ruff check . --fix`) em **commit isolado** noise-only
      (`275d4768`), sem misturar lógica. Reescreveu 39 arquivos + 95 auto-fixes seguros
      (remoção de BOM, aspas, ordenação de imports, `UP` para py314, f-strings vazias).
- [x] `.git-blame-ignore-revs` na raiz com o hash da baseline; git local configurado
      (`git config blame.ignoreRevsFile .git-blame-ignore-revs`). O GitHub usa o arquivo
      automaticamente; o time faz o `git config` uma vez.
- [x] **Triagem dos 54 avisos** que o `--fix` seguro não resolve, em **commit separado**
      da baseline: E722 (`except Exception:`), B904 (`raise ... from`), B905
      (`strict=False`), B023 (bind `val=val`), B007, F401/F811/F841 (remoção de código
      morto, preservando chamadas com efeito colateral e o re-export de `db`), com `# noqa`
      pontual e justificado apenas em B018 e E402 (imports após `sys.path.insert`).

> **Achados de código morto expostos pela triagem** (pré-existentes, candidatos a
> revisão futura — nenhum corrigido além da remoção do dead code): título com ServiceTag
> montado mas não renderizado no laudo (`termo_service.py`), `status_color` calculado sem
> uso (`notification_service.py`), traceback capturado sem ser logado (`admin.py`), e o
> parâmetro OAuth `state` lido sem validação anti-CSRF (`entra_auth.py`).

---

## 2. Gate de CI de lint

**Prioridade:** 🔺 Alta · **Status:** 🟡 Quase (workflow criado; falta o *required status check*)

**Por quê:** `pre-commit` local morre no primeiro `--no-verify`. O gate de CI é o que
**realmente** enforça num time de 1–2 devs ([ADR 0002](../adr/0002-ruff-para-lint-format-e-type-checking.md)).
O job de lint **não precisa de banco** (ao contrário do `pytest`) — deve ser um **job
separado e rápido**, que roda mesmo se o de testes falhar.

**Restrições concretas (da revisão por pares):**

- **Job próprio**, distinto do job de `pytest` ([testes/ROADMAP #1](../testes/ROADMAP.md))
  no mesmo workflow. Sem service container MySQL aqui.
- Fixar **Python 3.14** no job (= local e deploy, já alinhados — item #0).
- Usar a **mesma versão do Ruff** do `requirements-dev.txt` (instalar a partir dele, não
  um Ruff flutuante), senão volta o "verde local / vermelho no CI".
- O gate só protege se for **required status check** na branch protegida. Atenção ao
  fluxo real: deploy é push direto na `main` e o trabalho acontece na `develop` — o gate
  precisa rodar em **PR** (`develop` → `main`) para enforçar de fato.
- Cache de `pip` para não inflar o tempo do PR.

**Checklist:**

- [x] Job de CI (`.github/workflows/ci.yml`, job `lint`) em `pull_request` para `develop`
      e `main` que roda `ruff format --check .` e `ruff check .`. Instala **só** o Ruff na
      versão fixada, lendo-a do `requirements-dev.txt` (`grep '^ruff==' …`) — fonte única,
      sem drift e sem puxar o stack pesado da app (o lint não precisa de banco).
- [x] O job **falha o PR** em violação (sem `continue-on-error`); Python 3.14; cache de pip.
- [ ] **Marcar o job `Lint (Ruff)` como *required status check*** na proteção de branch da
      `main` (e `develop`, se protegida). **Ação manual no GitHub** (Settings → Branches),
      não versionável — sem isso o job roda mas não bloqueia o merge. **Passo a passo em
      [CONFIGURACAO_GIT.md](CONFIGURACAO_GIT.md#1-lint-ruff-como-required-status-check--a-pendência-bloqueante).**
- [x] Convive com o futuro gate de `pytest` ([testes/ROADMAP #1](../testes/ROADMAP.md)) — o
      `ci.yml` recebe o job de testes como um job separado (que aí sim precisa do MySQL).
- [x] Documentado no [índice de docs](../README.md) e no `CLAUDE.md` (lint obrigatório).

---

## 3. `pre-commit` + paridade de editor

**Prioridade:** ▪ Média · **Status:** ✅ Concluído (2026-06-30)

**Por quê:** conveniência — feedback local antes do push, e formatação automática no
editor para o dev nunca brigar com o gate. **Não é a fundação** (o CI é); é uma camada
de conforto que reduz idas e vindas no PR.

**Feito:**

- [x] `.pre-commit-config.yaml` com os hooks `ruff-check` (lint, `--fix`) + `ruff-format`,
      `rev: v0.15.20` **fixada** na mesma versão do `requirements-dev.txt` (o id atual é
      `ruff-check`; `ruff` é alias legado). `pre-commit>=3.7` adicionado ao
      `requirements-dev.txt`; ativar com `pre-commit install`.
- [x] `.editorconfig` na raiz (charset UTF-8, indentação, `max_line_length = 100` coerente
      com o Ruff; fim de linha deixado a cargo do git/`autocrlf`).
- [x] `.vscode/settings.json` (format-on-save + fix/organize-imports via Ruff,
      `importStrategy: fromEnvironment`) e `.vscode/extensions.json` (recomenda a extensão
      Ruff). O `.gitignore` passou a versionar só esses dois arquivos do `.vscode/`.

---

## 4. Type checking — adiado

**Prioridade:** ▫ Futuro · **Status:** ⚪ Adiado (condicional)

**Por quê:** o conselho foi enfático (4 de 5) — `mypy`/`pyright` estrito sobre um
codebase sem type hints gera milhares de erros inúteis e mata a iniciativa. ROI hoje é
~zero. O voto dissidente (tipos como combustível para IA) é reconhecido como **upside
futuro**, não trabalho de agora. Ver [ADR 0002](../adr/0002-ruff-para-lint-format-e-type-checking.md).

**Gatilho para reativar:** quando o time começar a **anotar tipos de propósito** (novos
módulos, contratos que valha proteger), ou se bugs de tipo passarem a recorrer.

**Quando reativar, o caminho:**

- [ ] Introduzir `pyright` em modo `basic` e **não-bloqueante** primeiro (advisory),
      rodando no editor em tempo real.
- [ ] Anotar **módulo a módulo**, começando pelos novos / mais críticos — nunca um
      *strict* retroativo sobre tudo.
- [ ] Só promover a bloqueante no CI depois que uma fatia relevante estiver tipada.

---

## Histórico (itens concluídos)

- 🟢 **2026-06-30** — Itens #1, #2 e #3 implementados na branch
  `chore/qualidade-ruff-baseline`. **#1:** `pyproject.toml` + `ruff==0.15.20` fixado;
  baseline (`ruff format` + `ruff check --fix`, 39 arquivos + 95 auto-fixes) em commit
  isolado `275d4768`, registrado no `.git-blame-ignore-revs`; triagem manual dos 54
  avisos restantes (E722/B904/B905/B023/B007/F401/F811/F841 corrigidos; `# noqa` só em
  B018 e E402). **#2:** `.github/workflows/ci.yml` com job `lint` (Ruff em PR para
  `develop`/`main`, sem banco, Python 3.14, versão do Ruff lida do `requirements-dev.txt`)
  — falta só marcar como *required status check* no GitHub. **#3:** `.pre-commit-config.yaml`
  (`ruff-check` + `ruff-format`, `rev` fixada), `.editorconfig`, `.vscode/settings.json` +
  `extensions.json`, `pre-commit>=3.7`. **Validação:** `ruff check .` + `ruff format --check .`
  verdes e a **suíte `pytest` completa passou — 274 testes verdes** contra o MySQL do
  container (`docker compose up -d`), confirmando que a baseline e a triagem não
  regrediram comportamento.
- 🟢 **2026-06-30** — Decisão registrada na
  [ADR 0002](../adr/0002-ruff-para-lint-format-e-type-checking.md) (veredito do Conselho
  de LLMs) e roadmap criado. Pré-requisito de paridade de Python resolvido: `mise.toml`
  subiu para 3.14, alinhando local e deploy ([P5 ✅](../infraestrutura/PRONTIDAO_PRODUCAO.md)).

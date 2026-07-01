# Configuração do Ruff no Git — o que **não** vive no repositório

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> Complementa o [ROADMAP de Qualidade](ROADMAP.md) (plano/status) e a
> [ADR 0002](../adr/0002-ruff-para-lint-format-e-type-checking.md) (o porquê).
>
> **Última atualização:** 2026-07-01 — criação. Reúne, num só lugar, as configurações
> do gate de Ruff que **não são versionáveis** (proteção de branch no GitHub e `git config`
> local por dev). Sem elas, o tooling existe no repo mas **não enforça**.

O código do gate de Ruff está todo versionado (`pyproject.toml`, `.github/workflows/ci.yml`,
`.pre-commit-config.yaml`, `.git-blame-ignore-revs`). Mas três configurações **moram fora do
repositório** — no GitHub e no `git config` de cada máquina — e por isso não entram por PR.
Esta é a pendência: enquanto não forem feitas, o gate roda mas não bloqueia, e o `git blame`
continua poluído pela baseline.

| # | Configuração | Onde | Quem | Bloqueante? | Estado |
|---|--------------|------|------|-------------|--------|
| 1 | Marcar `Lint (Ruff)` como *required status check* | GitHub (Settings → Branches) | Quem tem admin no repo | **Sim** — sem isso o merge não é bloqueado | ⛔ **Pendente** |
| 2 | `git config blame.ignoreRevsFile .git-blame-ignore-revs` | `git config` local | Cada dev, 1× por clone | Não (conveniência) | 🔁 Por dev |
| 3 | `pre-commit install` | `git` hooks local | Cada dev, 1× por clone | Não (conveniência) | 🔁 Por dev |

---

## 1. `Lint (Ruff)` como *required status check* — a pendência bloqueante

**Por quê:** o workflow [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) roda o job
`Lint (Ruff)` em todo PR para `develop` e `main`. Mas um job de CT que apenas *roda* não
impede o merge: o GitHub só **bloqueia** um PR com check vermelho quando esse check está
marcado como **required** na regra de proteção da branch. Sem esse passo, um PR com violação
de Ruff fica verde para merge e o gate vira decorativo — exatamente o ponto que a
[ADR 0002](../adr/0002-ruff-para-lint-format-e-type-checking.md) quer evitar (`pre-commit`
local morre no primeiro `--no-verify`; o CI required é o que realmente enforça).

**Pré-requisito:** o check só aparece na lista do GitHub **depois** que o job rodou ao menos
uma vez. Abra (ou atualize) um PR contra `main` para o workflow `CI` executar; aí o nome
`Lint (Ruff)` fica disponível para seleção.

**Passo a passo (precisa de permissão de admin no repositório):**

1. GitHub → repositório `YanWaltrick/ESTOQUE-1.0` → **Settings** → **Branches**.
2. Em **Branch protection rules**, edite a regra da `main` (crie uma com *Branch name pattern*
   `main` se ainda não existir).
3. Marque **Require status checks to pass before merging** e, abaixo, **Require branches to be
   up to date before merging**.
4. No campo de busca de checks, procure e adicione **`Lint (Ruff)`** (é o `name:` do job no
   `ci.yml` — não o nome do workflow, que é `CI`).
5. Salve (**Create** / **Save changes**).
6. Repita para a `develop` **se ela for uma branch protegida**. O fluxo real do projeto é
   PR `develop` → `main`, então a proteção da `main` é a que trava o merge; proteger a
   `develop` é reforço opcional.

**Como validar:** abra um PR de teste que introduza uma violação proposital (ex.: uma linha
com import não usado). O merge deve ficar **bloqueado** com o check `Lint (Ruff)` vermelho e a
mensagem "Required statuses must pass". Reverta a violação e confirme que o PR libera.

**Ao concluir:** marque o checkbox correspondente no [item #2 do ROADMAP](ROADMAP.md#2-gate-de-ci-de-lint)
e mova o status do item para ✅.

---

## 2. `git blame` ignorando a baseline — `blame.ignoreRevsFile` (por dev)

**Por quê:** a baseline do Ruff (`275d4768`) reformatou dezenas de arquivos de uma vez. Sem
configuração, `git blame` atribui essas linhas ao commit mecânico, escondendo o autor real. O
arquivo [`.git-blame-ignore-revs`](../../.git-blame-ignore-revs) (versionado) lista os commits
"noise-only" a ignorar, mas o `git` da máquina precisa ser **apontado** para ele — isso é
`git config` local, não entra por PR.

```bash
# Uma vez por clone (na raiz do repositório):
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

- O **GitHub já respeita** o `.git-blame-ignore-revs` automaticamente na interface de blame —
  o `git config` acima é só para o `git blame` **local** / na IDE.
- Ao adicionar um novo commit de reformatação em massa, registre o hash completo no
  `.git-blame-ignore-revs` (instruções no cabeçalho do próprio arquivo).

---

## 3. Hooks de `pre-commit` (por dev)

**Por quê:** o [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml) (versionado) declara os
hooks de Ruff, mas os hooks só passam a rodar depois de **instalados** no `.git/hooks` local —
outra configuração por máquina. É conveniência (feedback antes do push), **não** substitui o
gate de CI do item #1.

```bash
pip install -r requirements-dev.txt   # inclui pre-commit e o ruff fixado
pre-commit install                    # ativa os hooks neste clone
```

A partir daí, `ruff-check` (com `--fix`) e `ruff-format` rodam a cada commit. Para rodar em
todos os arquivos manualmente: `pre-commit run --all-files`.

---

## Resumo

O único item **bloqueante e centralizado** é o **#1** (required status check) — depende de uma
pessoa com admin no GitHub e é o que falta para o gate de Ruff realmente proteger a `main`. Os
itens **#2** e **#3** são por desenvolvedor e recorrentes a cada novo clone (registre-os no
[ONBOARDING](../ONBOARDING.md) para novos membros).

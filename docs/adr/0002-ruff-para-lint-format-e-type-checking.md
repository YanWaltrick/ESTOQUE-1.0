# ADR 0002 — Ruff para lint + formatação; type checking adiado

> Registro de Decisão de Arquitetura (ADR). Segue a
> [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md) e a convenção
> `docs/adr/NNNN-titulo.md` definida no [`CLAUDE.md`](../../CLAUDE.md).
>
> **Status:** ✅ Aceita · **Data:** 2026-06-30
> **Origem:** veredito do Conselho de LLMs sobre tooling de qualidade de código (2026-06-30).
> **Plano de execução:** [Qualidade de Código — Roadmap](../qualidade/ROADMAP.md).

---

## Contexto

O projeto não tinha **nenhum** tooling de qualidade de código: sem `pyproject.toml`,
sem linter, sem formatador, sem type checker e sem `pre-commit`. As dependências de
desenvolvimento eram apenas `pytest` + `pytest-cov`. O codebase é pequeno-médio
(~25 arquivos `.py` em `app/` + ~12 de teste + alguns scripts utilitários), sem type
hints, mantido por um time de 1–2 devs.

Em paralelo, o time está montando o **gate de CI** (item #1 do
[Roadmap de Testes](../testes/ROADMAP.md)) — hoje o único workflow só faz deploy para a
Azure a cada push na `main`, sem rodar nada antes. Surgiu a pergunta: **qual a melhor
maneira de implementar lint + formatação + type checking?** As decisões em aberto eram:
quais ferramentas (Ruff vs. `black`+`flake8`+`isort`; `mypy` vs. `pyright`), quão
estrito começar, gradual vs. tudo de uma vez, e onde rodar (pre-commit local, gate de
CI, ou ambos).

O risco de errar é concreto: tooling pesado demais, regras estritas demais sobre um
codebase sem tipos, ou um setup que ninguém mantém — qualquer um gera milhares de erros
no primeiro run, frustra o time e faz a iniciativa ser abandonada.

## Decisão

1. **Lint + formatação: adotar o [Ruff](https://docs.astral.sh/ruff/), e só ele.** Uma
   ferramenta, um arquivo de config (`pyproject.toml`), substitui `black` + `flake8` +
   `isort` + `pyupgrade` + `bugbear`. Começar com um conjunto **mínimo** de regras
   (`E`, `F`, `I`, mais `UP` e `B`), não o catálogo inteiro.
2. **Aplicar a baseline de uma vez**, num único commit "noise-only"
   (`ruff format` + `ruff check --fix`), registrado em `.git-blame-ignore-revs` para
   não destruir o `git blame`.
3. **Enforçar via gate de CI bloqueante** — um job dedicado e rápido (sem banco),
   separado do job de `pytest`, exigido como *status check* obrigatório em PRs. O
   `pre-commit` local é conveniência opcional, **não** a fundação.
4. **Adiar o type checking.** Não adotar `mypy`/`pyright` estrito agora. Quando o time
   começar a anotar tipos de propósito, introduzir `pyright basic` em modo
   **não-bloqueante** primeiro, módulo a módulo.

## Por quê (veredito do Conselho de LLMs)

Convergência quase unânime dos cinco conselheiros, confirmada pela revisão por pares:

1. **Ruff, e só Ruff.** Os cinco descartaram o stack `black`+`flake8`+`isort`. Ruff é
   esse stack num binário só, com uma config, rodando em milissegundos. Em 2026, num
   codebase zerado, "Ruff vs. flake8" é uma falsa escolha.
2. **Type checking adiado** (4 de 5, e a revisão por pares marcou o dissidente como o
   maior ponto cego). `mypy`/`pyright` sobre código sem type hints é "corretor
   ortográfico numa página em branco": ou roda *lenient* e não pega nada (teatro de
   qualidade), ou roda *strict* e cospe milhares de erros que ninguém corrige — a forma
   mais confiável de matar a iniciativa. O ROI hoje é ~zero; tipos rendem **quando se
   anota de propósito**, não ligando um checker sobre o legado.
3. **O gate de CI é o que realmente enforça.** `pre-commit` local morre no primeiro
   `git commit --no-verify`. Num time de 1–2 devs, a única verdade que não dá para
   esquecer de instalar é o CI.
4. **Baseline de uma vez, não gradual.** Lint gradual deixa ruído eterno no diff;
   formatar tudo num commit isolado resolve e some.

**Voto dissidente registrado (O Expansionista):** type hints como "combustível para
desenvolvimento assistido por IA" (autocomplete, refatoração segura, geração de testes
que batem). O conselho reconhece o upside, mas ele só se materializa com anotação
deliberada — por isso vira **roadmap futuro**, não o agora.

**Pontos cegos pegos na revisão por pares** (nenhum conselheiro individual viu) e já
incorporados ao plano:

- **Fixar a versão do próprio Ruff** (em `requirements-dev.txt` e no `.pre-commit-config`).
  Ruff é binário estático — o que causa "verde local / vermelho no CI" não é a versão do
  Python, é um **release novo do Ruff** trazendo regras novas.
- **Separar o job de lint do de testes:** o `pytest` precisa de MySQL de pé; o Ruff não
  precisa de banco. Job próprio, rápido, roda mesmo se os testes falharem.
- **O gate só vale se for *required status check*** na branch protegida — e o fluxo real
  (deploy é push direto na `main`, devs trabalham na `develop`) precisa de PR para o gate
  enforçar de fato.
- **`.editorconfig` + format-on-save** no editor, para alinhar o dev ao CI.

## Consequências

- **Positivas:** feedback de estilo/erros quase instantâneo; PRs mais limpos; uma única
  config e um único binário de baixo custo de manutenção; `UP` moderniza sintaxe para
  3.14 automaticamente; baseline única encerra discussões de formatação.
- **Atenção / contingência:** o primeiro `ruff format` reescreve muitos arquivos — **tem
  de** ser commit isolado + `.git-blame-ignore-revs`, senão polui o `blame`. A versão do
  Ruff **tem de** ser fixada, senão o CI quebra sozinho num upgrade. O gate só protege se
  o trabalho passar por PR com status check obrigatório.
- **Quando reabrir esta ADR:** se o codebase crescer a ponto de o type checking estrito
  passar a valer a pena (contratos a proteger, mais devs, bugs de tipo recorrentes) —
  momento de promover `pyright`/`mypy` de *advisory* para bloqueante. Ou se o Ruff deixar
  de cobrir alguma necessidade que justifique uma ferramenta dedicada.

## Decisões relacionadas

- **Gate de CI (`pytest`):** [Roadmap de Testes #1](../testes/ROADMAP.md) — o job de lint
  e o de testes convivem no mesmo workflow, como **jobs separados**.
- **Paridade de Python (3.14):** [P5 em PRONTIDAO_PRODUCAO.md](../infraestrutura/PRONTIDAO_PRODUCAO.md)
  — resolvido junto desta decisão (local alinhado ao deploy em 3.14), o que fixa o
  `target-version` do Ruff e a versão do job de CI.
- **Decisão de stack (Flask):** [ADR 0001](0001-manter-flask-como-stack.md).

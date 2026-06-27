# Norma de Documentação Viva — Sistema ESTOQUE

> **Princípio central:** a documentação tem prioridade sobre o código. Antes de
> escrever ou alterar código, o estado, a decisão e o próximo passo devem estar
> registrados aqui. Assim o contexto vive nos arquivos do repositório, não na
> memória de uma conversa — e é seguro "dar clear no chat" a qualquer momento.

---

## 1. Por que documentação viva

Uma conversa de chat é volátil: ao limpá-la, perde-se o raciocínio, as pendências
e as decisões. Documentação **viva** é o oposto — um conjunto de arquivos que:

- Refletem sempre o **estado atual** do projeto (não um retrato congelado no tempo).
- São atualizados **na mesma tarefa** em que o código muda (nunca "depois").
- Servem como **memória persistente** do projeto, recuperável por qualquer pessoa
  (ou agente) sem depender do histórico de uma conversa.

Se o código e a documentação divergirem, **a documentação errada é um bug** — trate
com a mesma seriedade de um teste quebrado.

---

## 2. Onde mora cada coisa

| Tipo de conteúdo | Local |
|------------------|-------|
| Visão geral e comandos do projeto | [`README.md`](../README.md) (raiz) |
| Guia para agentes (Claude Code) | [`CLAUDE.md`](../CLAUDE.md) (raiz) |
| Índice de toda a documentação | [`docs/README.md`](README.md) |
| Análises, guias e políticas | `docs/*.md` |
| Documentação por área/feature | `docs/<area>/` (ex.: [`docs/testes/`](testes/), [`docs/entra-id/`](entra-id/)) |
| **Pendências e próximos passos** | `docs/<area>/ROADMAP.md` |

> Toda área com trabalho em andamento deve ter um `ROADMAP.md` próprio. É lá que
> as pendências vivem — não em comentários `TODO` soltos no código nem no chat.

---

## 3. Convenções de um documento vivo

Todo documento vivo (README de área e ROADMAP) segue estas regras:

1. **Cabeçalho com data de atualização.** A primeira seção registra
   `Última atualização: AAAA-MM-DD` e, se útil, a branch/contexto.
2. **Status explícito.** Itens de trabalho usam um destes marcadores:

   | Marcador | Significado |
   |----------|-------------|
   | 🔴 Pendente | Ainda não iniciado |
   | 🟡 Em andamento | Começou, não concluído |
   | 🟢 Concluído | Feito e verificado |
   | ⚪ Descartado | Decidiu-se não fazer (com motivo) |

3. **Prioridade declarada** (`Alta` / `Média` / `Baixa`) para todo item pendente.
4. **Origem da decisão.** Quando uma pendência nasce de uma análise (ex.: veredito
   do conselho, revisão de segurança), registre a fonte — o "porquê" não se perde.
5. **Checklists acionáveis.** Cada item descreve o primeiro passo concreto, não só
   a intenção.

---

## 4. Fluxo de manutenção

Ao concluir qualquer tarefa relevante:

1. Atualize o `ROADMAP.md` da área: mude o status, marque checklists, mova itens
   concluídos para o histórico.
2. Atualize a `Última atualização` do documento.
3. Se a estrutura de pastas/arquivos mudou, atualize o índice em
   [`docs/README.md`](README.md).
4. Só então (ou em paralelo) faça o commit do código.

> Regra prática: **um PR/commit que muda comportamento sem tocar na documentação
> correspondente está incompleto.**

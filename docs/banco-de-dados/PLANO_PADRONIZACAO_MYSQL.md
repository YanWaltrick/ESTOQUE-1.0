# Plano: Padronização em MySQL (um dialeto em todos os ambientes)

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> **Status geral:** 🔴 Planejado — **NÃO implementado** (decisão explícita de só documentar por ora).
>
> **Última atualização:** 2026-06-27 — branch `feature/implementacao-testes`

---

## 1. Decisão e contexto

**Decisão:** padronizar o **MySQL** como único motor de banco em **todos** os
ambientes (produção, desenvolvimento, teste e CI). Eliminar o SQLite. **Não**
introduzir PostgreSQL.

**Por que (resumo do veredito do Conselho de LLMs):**

- Ambiente de teste deve falar o **mesmo dialeto de produção**. Prod é MySQL
  (Azure App Service) → teste/CI também devem ser MySQL. Isso elimina a classe de
  bug "passou no teste, quebrou em prod".
- Introduzir Postgres criaria um **terceiro dialeto** para resolver um problema que
  MySQL local resolve igual. O fato de "haver um Postgres rodando local" é
  conveniência, não argumento de engenharia.
- **Critério correto: "casar com produção", não "fidelidade total".** Prod é
  *Azure Database for MySQL gerenciado* (versão, `sql_mode`, `charset/collation`,
  `max_allowed_packet` específicos). Um container `mysql` com defaults ≠ Azure.
  A fidelidade só é real se o container **pinar versão + `sql_mode` + collation**
  iguais aos da Azure — caso contrário é teatro de fidelidade.
- O bug que disparou tudo (isolamento de testes quebrado) é de **fixture + driver
  pysqlite**, independente do banco. Migrar para MySQL o resolve de forma limpa
  (transação externa real), mas as duas coisas são decisões separadas.

> Produção MySQL fica **intocada** por este plano. Migrar dados de produção (ou
> trocar o motor de prod) está **fora de escopo** — só se justifica por razão de
> negócio, não por testes.

---

## 2. Estado atual × Alvo

| Aspecto | Hoje | Alvo |
|---------|------|------|
| Produção | MySQL (Azure) | MySQL (Azure) — inalterado |
| Dev local | SQLite (default em `database.py`) | MySQL via container |
| Testes | SQLite temporário (isolamento **quebrado**) | MySQL via container, isolamento por transação externa |
| CI | Não roda testes | `pytest` contra MySQL (`services: mysql` no GitHub Actions) |
| `DocumentoArquivo.content` | `LargeBinary` → `BLOB` (limite 64 KB no MySQL) | `LONGBLOB` explícito |
| Schema | Alembic + fallback `_ensure_schema_columns` (ALTER TABLE no boot) | Alembic como única fonte; fallback removido |

---

## 3. Pendências bloqueantes

| ID | Pendência | Prioridade | Status |
|----|-----------|-----------|--------|
| PEND-1 | **Descobrir a versão exata do MySQL no Azure** (`SELECT VERSION();`, `SELECT @@sql_mode;`, collation) | 🔺 Alta | 🔴 Pendente |
| PEND-2 | **Implementar o container Docker** (`docker-compose.yml` + conftest apontando para MySQL) | 🔺 Alta | 🔴 Pendente (adiado por decisão) |

**PEND-1 — versão do Azure desconhecida.** Não temos a versão/`sql_mode`/collation
que a Azure roda. **Decisão provisória:** o plano assume `mysql:8.0` como padrão
sensato (placeholder). Ao descobrir a versão real, ajustar o pin no
`docker-compose.yml` e nesta tabela. Onde verificar: Azure Portal → recurso MySQL →
*Overview / Server version*, ou rodar `SELECT VERSION();` / `SELECT @@sql_mode;` no
banco de produção.

**PEND-2 — Docker adiado.** A decisão atual é **documentar, não implementar**. O
container MySQL e a troca do `conftest.py` para MySQL **não serão feitos agora**;
ficam registrados aqui como próximo passo quando o plano for retomado. Usar
**Docker** (e não podman) na implementação.

---

## 4. Plano de execução (quando retomado)

Todas as etapas estão 🔴 Pendentes — nenhuma implementada.

- [ ] **E1. Container MySQL versionado.** `docker-compose.yml` na raiz com MySQL
      **pinado** à versão do Azure (placeholder `mysql:8.0` até PEND-1), `sql_mode`
      e collation iguais aos de prod. Banco de teste dedicado (`estoque_test`).
- [ ] **E2. `conftest.py` → MySQL.** `DATABASE_URL` de teste apontando para o
      container; fixture `db_session` com transação externa real (resolve o
      isolamento de verdade, sem o workaround do pysqlite).
- [ ] **E3. Teste de isolamento.** Teste que escreve no banco e confirma rollback —
      prova empírica de que o isolamento funciona (hoje não exercitado).
- [ ] **E4. Corrigir `LargeBinary` → `LONGBLOB`** no modelo `DocumentoArquivo`
      (`app/models/__init__.py`), evitando truncamento silencioso de documentos
      > 64 KB no MySQL.
- [ ] **E5. Matar `_ensure_schema_columns`.** Mover as colunas para uma migration
      Alembic versionada e remover o fallback de `ALTER TABLE` no boot
      (`app/__init__.py`).
- [ ] **E6. Remover o SQLite.** Atualizar `database.py` (sem fallback SQLite),
      `requirements*` se aplicável, e a documentação de onboarding. Definir como os
      devs sobem o MySQL local (`docker compose up`).
- [ ] **E7. Gate de CI.** Job no GitHub Actions com `services: mysql` rodando
      `pytest` e bloqueando merge/deploy em caso de falha.
- [ ] **E8. Atualizar docs vivos.** `CLAUDE.md`, `docs/testes/README.md` e os
      ROADMAPs refletindo o novo padrão; marcar etapas como 🟢 conforme concluídas.

---

## 5. Cuidados não-negociáveis

1. **Pin de fidelidade (E1).** Sem fixar versão + `sql_mode` + collation iguais aos
   da Azure, a justificativa inteira da decisão ("casar com prod") vira teatro.
2. **`LONGBLOB` (E4).** `LargeBinary` puro vira `BLOB` (64 KB) no MySQL — documento
   maior trunca em silêncio ou estoura `max_allowed_packet`. O SQLite escondia isso.
3. **A fixture é o conserto do isolamento, não o banco.** O MySQL viabiliza a
   receita de transação externa, mas o defeito original é de fixture. Provar com E3.
4. **Não explorar features só porque dá.** JSON nativo, FULLTEXT, generated columns
   etc. são escopo que ninguém pediu e aumentam lock-in. Manter o modelo enxuto.

---

## 6. Fora de escopo

- Migrar **dados de produção** ou trocar o motor de prod (só por razão de negócio).
- Adotar **PostgreSQL** (descartado).
- Adotar features específicas do MySQL além do necessário (ver cuidado #4).

---

## 7. Relação com outros documentos

- Substitui a abordagem interina de testes em SQLite descrita em
  [`docs/testes/README.md`](../testes/README.md).
- Absorve os itens [`ROADMAP` #8 e #9](../testes/ROADMAP.md) (isolamento quebrado e
  limpeza do SQLite temporário): ambos deixam de ser corrigidos no SQLite e passam a
  ser resolvidos pela migração para MySQL (etapas E2/E3).
- Decisão registrada a partir do veredito do Conselho de LLMs (2026-06-27).

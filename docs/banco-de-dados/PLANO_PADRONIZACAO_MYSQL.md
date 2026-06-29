# Plano: Padronização em MySQL (um dialeto em todos os ambientes)

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> **Status geral:** 🟡 Em implementação — E1/E2/E4/E6 aplicados (container MySQL já
> sobe via `docker compose up -d`); E3/E5/E7 pendentes; E8 parcial.
>
> **Última atualização:** 2026-06-27 — remoção do SQLite (100% MySQL)

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
| Dev local | MySQL via container (SQLite removido) | MySQL via container |
| Testes | MySQL via container, isolamento por transação externa | MySQL via container, isolamento por transação externa |
| CI | Não roda testes | `pytest` contra MySQL (`services: mysql` no GitHub Actions) |
| `DocumentoArquivo.content` | `LONGBLOB` (E4 aplicado) | `LONGBLOB` explícito |
| Schema | Alembic + fallback `_ensure_schema_columns` (ALTER TABLE no boot) | Alembic como única fonte; fallback removido |

---

## 3. Pendências bloqueantes

| ID | Pendência | Prioridade | Status |
|----|-----------|-----------|--------|
| PEND-1 | **Descobrir a versão exata do MySQL no Azure** (`SELECT VERSION();`, `SELECT @@sql_mode;`, collation) | 🔺 Alta | 🔴 Pendente |
| PEND-2 | **Implementar o container Docker** (`compose.yml` + conftest apontando para MySQL) | 🔺 Alta | 🟢 Feito (`compose.yml` + `conftest`→`estoque_test`) |

**PEND-1 — versão do Azure desconhecida.** Não temos a versão/`sql_mode`/collation
que a Azure roda. **Estado atual:** o `compose.yml` já está **pinado em
`mysql:8.0`** como placeholder sensato (e os drivers — `pymysql 1.1.1` +
`cryptography` — suportam o `caching_sha2_password` do MySQL 8). Ao descobrir a
versão real, **trocar pelo patch exato** (ex.: `mysql:8.0.39`) no `compose.yml`
e nesta tabela, e alinhar `sql_mode`/collation. Como verificar — rodar no banco de
**produção** (Azure):

```sql
SELECT VERSION();
SELECT @@sql_mode;
SELECT @@collation_server;
```

Ou no Azure Portal → recurso MySQL → *Overview / Server version*.

**PEND-2 — Concluída.** O container MySQL (`compose.yml`) e a troca do
`conftest.py` para MySQL (`estoque_test`) **já foram implementados** (ver E1/E2). O
ambiente usa **Docker** (`docker compose up -d`). Resta apenas o gate de CI (E7)
para rodar a suíte contra esse MySQL automaticamente.

---

## 4. Plano de execução

- [x] **E1. Container MySQL versionado.** `compose.yml` na raiz com MySQL
      pinado (`mysql:8.0` até PEND-1), `sql_mode` e collation `utf8mb4`. Banco de
      teste dedicado (`estoque_test`) via `scripts/mysql-init/01-init.sql`.
- [x] **E2. `conftest.py` → MySQL.** `DATABASE_URL` de teste aponta para
      `estoque_test` (sobrescrevível por `TEST_DATABASE_URL`); `db_session` usa a
      receita de transação externa (já agnóstica de dialeto).
- [ ] **E3. Teste de isolamento.** Sonda existe (validada no SQLite); falta
      promovê-la a teste permanente e confirmar contra o MySQL.
- [x] **E4. `LargeBinary` → `LONGBLOB`** no modelo `DocumentoArquivo`
      (`app/models/__init__.py`). *Obs.:* `create_all` aplica em bancos novos; um
      banco já existente exige migration `ALTER TABLE ... MODIFY content LONGBLOB`.
- [ ] **E5. Matar `_ensure_schema_columns`.** Mover as colunas para uma migration
      Alembic versionada e remover o fallback de `ALTER TABLE` no boot
      (`app/__init__.py`).
- [x] **E6. Remover o SQLite.** `database.py` exige `DATABASE_URL` (sem fallback),
      `connect_args` de SQLite removido, `migrations/{alembic.ini,env.py}` sem
      SQLite, `.env*` e docs de onboarding atualizados.
- [ ] **E7. Gate de CI.** Job no GitHub Actions com `services: mysql` rodando
      `pytest` e bloqueando merge/deploy em caso de falha.
- [~] **E8. Atualizar docs vivos.** `CLAUDE.md`, `PLANO`, `docs/testes/*`,
      `ARQUITETURA.md`, `SECURITY.md` atualizados. Concluir conforme E3/E5/E7.
- [ ] **E9. Limpeza de dependências.** `mysql-connector-python` no `requirements.txt`
      **não é usado** (o driver real é `pymysql`); remover após confirmar que nenhum
      ambiente/serviço depende dele.
- [ ] **E10. `LONGBLOB` em bancos existentes.** `create_all` (E4) só afeta bancos
      novos. Em um banco já existente (ex.: produção), aplicar
      `ALTER TABLE documentos_arquivos MODIFY content LONGBLOB;` via migration Alembic
      versionada — senão a coluna continua `BLOB` (limite 64 KB) lá.

> ⚠️ **Verificação pendente:** rodar `flask --app manage db upgrade` + `pytest`
> contra o container MySQL (não feito ainda — o container precisa estar de pé).

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

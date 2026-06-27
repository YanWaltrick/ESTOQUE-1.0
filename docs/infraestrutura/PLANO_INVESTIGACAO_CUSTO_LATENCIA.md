# Plano: Investigação de Custo & Latência (Azure)

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> **Status geral:** 🔴 Investigação não iniciada. Decisão de provedor: **permanecer na Azure por ora.**
>
> **Última atualização:** 2026-06-27 — branch `feature/implementacao-testes`

---

## 1. Decisão e contexto

**Sintomas:** (1) custo alto — **R$ 1.500/mês** (confirmado em reais, ~US$ 280);
(2) alta latência.

**Decisão:** **não migrar de provedor** (nem AWS, nem outro) antes de medir e
corrigir código/configuração. A causa raiz é quase certamente do app/config, e
viajaria junto para qualquer nuvem.

**Por que (veredito unânime do Conselho de LLMs, 2026-06-27):**

- Os dois culpados estruturais são do **app**, não da nuvem:
  - **Documentos binários dentro do MySQL** (`DocumentoArquivo.content = LargeBinary`)
    — destroem o buffer pool, multiplicam IO, incham backup. A latência provável é
    o banco varrendo páginas cheias de PDF. **No RDS/AWS seria idêntico.**
  - **`_ensure_schema_columns` rodando `ALTER TABLE` a cada boot** — DDL não é
    transacional em MySQL; trava a tabela, gera cold start lento e risco de
    corrupção sob concorrência. Nenhum provedor conserta isso.
- **Nada foi medido ainda.** Decidir uma migração de ~R$ 18 mil/ano sem abrir o
  billing é "cirurgia sem exame".
- **Lock-in invertido:** Entra ID, Teams e e-mail são Microsoft. Migrar para a AWS
  adiciona atrito sem remover a dependência do ecossistema MS.
- A magnitude (R$ 1.500/mês) sugere **tier do MySQL superdimensionado** (provável
  General Purpose segurando os BLOBs) mais do que o App Service.

> Se, **depois** de medir e otimizar, a Azure ainda sair cara para este caso, o
> destino lógico é algo simples e barato (**VPS/Hetzner**) — **não a AWS**.

---

## 2. Diagnóstico — medir ANTES de mexer

| ID | Ação | Onde | Status |
|----|------|------|--------|
| D1 | Cost analysis **agrupado por recurso** (descobre quem come o orçamento) | Azure Portal → Cost Management → Cost analysis | 🔴 Pendente |
| D2 | Verificar SKU/tier reais e métricas de CPU/RAM | App Service → Scale up; MySQL → Compute+Storage | 🔴 Pendente |
| D3 | Medir onde mora a latência (timing de request vs. query) | APM / logs de request; `EXPLAIN` nas queries quentes | 🔴 Pendente |
| D4 | Confirmar **região** do App Service vs. MySQL vs. usuários (Brasil) | Portal (Overview de cada recurso) | 🔴 Pendente |
| D5 | Medir tamanho do banco e quanto é BLOB (`DocumentoArquivo`) | `SELECT` de tamanho por tabela | 🔴 Pendente |

> **Métrica de sucesso (definir após D1–D5):** qual custo/latência alvo tornaria a
> investigação "concluída" — e qual número justificaria, no futuro, cogitar troca
> de provedor.

---

## 3. Plano de ação priorizado (após diagnóstico)

- [ ] **A1. Tirar migrations/ALTER do boot.** `_ensure_schema_columns` e o
      `upgrade` devem rodar **no deploy**, não no start da aplicação
      (`app/__init__.py`). Baixo esforço (~1h), derruba cold start. 🔺 Alta
- [ ] **A2. Revisar SKU.** Descer 1-2 tiers do App Service e/ou MySQL se as
      métricas (D2) mostrarem folga. Economia imediata, zero migração. 🔺 Alta
- [ ] **A3. Corrigir região** se App Service e MySQL estiverem distantes entre si
      ou dos usuários (D4). Ganho de latência "de um clique". ▪ Média
- [ ] **A4. Mover documentos do MySQL para Blob Storage** — ataca custo (banco
      menor → SKU menor) **e** latência. **Maior item, porém o mais arriscado** —
      ver cuidados na seção 4. 🔺 Alta (com ressalvas)

---

## 4. Cuidados não-negociáveis (achados da revisão por pares)

1. **Tirar binários do banco NÃO é um toggle.** Exige reescrever a camada de servir
   documentos (hoje lê do banco), migrar os dados já gravados, e tratar
   consistência ponteiro↔arquivo + rollback.
2. **Entender por que os blobs estão no banco antes de reverter.** O script
   `scripts/migrate_docs_to_db.py` moveu documentos **do disco para o banco de
   propósito** — houve uma intenção de design (provável backup atômico / loja
   única). Reverter sem entender pode quebrar esse requisito.
3. **Segurança/LGPD.** Os PDFs são dados pessoais de colaboradores (ex.: Termo de
   Entrega). Mover para Blob Storage muda o modelo de exposição: controle de
   acesso, criptografia, URLs assinadas, backup consistente.
4. **A latência pode ser de rede/região** (Brasil ↔ região Azure), independente do
   banco. Não otimize o banco achando que é a causa antes de D3/D4.

---

## 5. Fora de escopo

- Migrar para **AWS** (pior destino: mais complexidade, mesmo problema).
- Qualquer troca de provedor **antes** de medir e otimizar.

---

## 6. Pendências

| ID | Pendência | Status |
|----|-----------|--------|
| PEND-INFRA-1 | Executar o diagnóstico D1–D5 (medir antes de mexer) | 🔴 Pendente |
| PEND-INFRA-2 | Definir a métrica de sucesso de custo/latência | 🔴 Pendente |
| PEND-INFRA-3 | Investigar a intenção de design por trás de blobs-no-banco antes de A4 | 🔴 Pendente |

---

## 7. Relação com outros documentos

- Conecta com o [Plano de Padronização MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md):
  a correção de `LargeBinary → LONGBLOB` e a remoção do `_ensure_schema_columns`
  aparecem nos dois planos. A diferença de armazenamento (BLOB no banco vs. Blob
  Storage) é decisão de arquitetura de dados a resolver em conjunto.
- Decisão registrada a partir do veredito do Conselho de LLMs (2026-06-27).

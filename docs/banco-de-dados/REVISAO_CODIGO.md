# Registro de Revisões de Código — Banco de Dados

> Documento vivo. Segue a [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
> Log acumulativo das revisões de código que tocam scripts e migrações de dados.
>
> **Última atualização:** 2026-06-27 — revisão `xhigh` com correção aplicada

---

## 2026-06-27 — `scripts/migrate_docs_to_db.py` (revisão `xhigh`, achado X3)

**Contexto:** ao mover os utilitários para `scripts/` (commit `e03554a`), o script de
migração de documentos do disco para o banco deixou de funcionar. A revisão `xhigh`
executou o script e confirmou **dois** defeitos somados.

**Sintoma (reproduzido):** `python scripts/migrate_docs_to_db.py` falhava antes de
migrar qualquer arquivo.

### Defeitos

1. **Colisão de tabela (pré-existente, do upstream).** O script redefinia
   `class DocumentoArquivo(db.Model)` inline com `__tablename__ = 'documentos_arquivos'`.
   Como importar o pacote `app` já registra o `DocumentoArquivo` de
   `app/models/__init__.py` no mesmo `db.metadata`, a redefinição levantava
   `InvalidRequestError: Table 'documentos_arquivos' is already defined`. Isso já
   quebrava o script antes mesmo do *move*.

2. **Path quebrado pelo *move* (regressão deste diff).** `uploads_dir` usava
   `os.path.dirname(__file__)`, que na raiz resolvia para `<raiz>/static/...`, mas em
   `scripts/` passou a resolver para `scripts/static/uploads/documentos` (inexistente)
   → `sys.exit(1)` com "Pasta de uploads não encontrada". A linha do `sys.path` foi
   ajustada no *move*, mas esta não.

### Correção aplicada

- Removida a classe inline; passou a **reutilizar o modelo canônico**
  `from app.models import DocumentoArquivo` (DRY, alinhado ao `CLAUDE.md`: não
  reimplementar o que o código já tem).
- Introduzida a constante `PROJECT_ROOT` (raiz do projeto), usada **tanto** no
  `sys.path.insert` **quanto** em `uploads_dir` — eliminando a divergência de path.

### Verificação

Execução end-to-end contra um SQLite temporário (sem `--delete`): migrou **41
arquivos** de `static/uploads/documentos/`, com 41 linhas em `documentos_arquivos`.
Nenhum erro de colisão ou de path.

> **Pendência relacionada:** o script ainda não tem teste automatizado. Quando a
> cobertura de scripts entrar no [ROADMAP de testes](../testes/ROADMAP.md), incluir um
> caso que rode a migração contra um diretório temporário.

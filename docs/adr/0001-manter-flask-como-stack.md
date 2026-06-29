# ADR 0001 — Manter Flask como stack de aplicação

> Registro de Decisão de Arquitetura (ADR). Segue a
> [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md) e a convenção
> `docs/adr/NNNN-titulo.md` definida no [`CLAUDE.md`](../../CLAUDE.md).
>
> **Status:** ✅ Aceita · **Data:** 2026-06-29
> **Origem:** veredito do Conselho de LLMs sobre a escolha de stack (2026-06-29).

---

## Contexto

A aplicação (`sistema-estoque`) é um sistema interno de controle de estoque sendo
amadurecido para produção na **Azure App Service**. A stack atual:

- **Flask 3.1** (application factory), Flask-SQLAlchemy, Flask-Login, Flask-WTF
  (CSRF), Flask-Migrate, Flask-Mail.
- **Templates Jinja2 renderizados no servidor** (~13 templates) — **não é SPA**.
- **MySQL** gerenciado na Azure (PyMySQL); deploy via GitHub Actions; servido com
  gunicorn (Linux) / waitress (Windows).
- Integração corporativa Microsoft: **SSO Entra ID** (MSAL) e notificações **Teams**.
- Geração de PDF (ReportLab), RBAC (admin/usuário), suporte CLT/PJ.
- **~8.000 linhas de Python já escritas** e uma suíte pytest (~76% de cobertura).

Surgiu a dúvida: seguir com Flask até produção é válido, ou conviria reconsiderar a
stack (Django, FastAPI, Node) antes do go-live?

## Decisão

**Manter Flask.** Não há justificativa para reescrever a stack de aplicação. Para um
app server-rendered desse porte — CRUD interno, da ordem de dezenas a baixas centenas
de usuários, RBAC, SSO e geração de documentos — Flask + Jinja é o caso de uso
canônico e cobre a carga esperada com folga.

## Por quê (veredito do Conselho de LLMs)

Convergência praticamente unânime dos cinco conselheiros, em três pontos:

1. **A pergunta de stack é a menos importante.** O framework é a parte de **menor
   risco** de todo o projeto. Reescrever ~8.000 linhas queimaria semanas para
   resolver um problema que não existe — "otimização prematura disfarçada de
   prudência".
2. **O risco real é operacional, não de framework.** "Compila na Azure" ≠ "pronto
   para produção". É na **montagem do deploy** (migrations no boot, armazenamento
   efêmero, credencial default, secrets, observabilidade) que este sistema vai
   quebrar — ver [Prontidão para Produção](../infraestrutura/PRONTIDAO_PRODUCAO.md).
3. **A base já é um ativo de integração corporativa.** Flask + Entra ID + Teams +
   `api_bp` já entregam um runtime reutilizável. A expansão (API REST/OpenAPI, bot de
   Teams, Power BI) é roadmap natural **depois** do endurecimento — não antes, sob
   pena de ampliar a superfície de ataque sobre uma fundação ainda insegura.

## Consequências

- **Positivas:** zero custo de migração; aproveita a suíte de testes, o SSO e as
  integrações já prontas; mantém o sweet spot de custo/manutenção do SSR em App
  Service; preserva o caminho de evolução para expor a API sem reescrever o backend.
- **Atenção / contingência:** a validação de "Flask serve" **não** significa "pronto
  para produção". A decisão fica condicionada a tratar os bloqueios de prontidão
  rastreados em [`PRONTIDAO_PRODUCAO.md`](../infraestrutura/PRONTIDAO_PRODUCAO.md)
  antes do go-live.
- **Quando reabrir esta ADR:** somente diante de uma mudança qualitativa de
  requisito que o SSR não atenda bem — p.ex. virar produto multi-tenant de larga
  escala, exigir tempo real intenso (websockets/streaming) ou um front-end SPA
  pesado que torne o template Jinja inadequado. Nenhum desses é o caso hoje.

## Decisões relacionadas

- **Provedor (Azure vs. outros):** permanecer na Azure por ora — ver
  [Investigação de Custo & Latência](../infraestrutura/PLANO_INVESTIGACAO_CUSTO_LATENCIA.md).
- **Banco (MySQL em todos os ambientes):** ver
  [Plano de Padronização MySQL](../banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md).

# Documentação — Sistema ESTOQUE

Índice da documentação do projeto. O ponto de entrada geral é o [README.md](../README.md) na raiz.

## Conteúdo

| Documento | Descrição |
|-----------|-----------|
| [ONBOARDING.md](ONBOARDING.md) | Passo a passo para rodar a aplicação localmente do zero (pré-requisitos, MySQL via Docker, venv, `.env`, troubleshooting). Comece por aqui. |
| [ARQUITETURA.md](ARQUITETURA.md) | Visão geral da arquitetura e fluxogramas (inicialização, requisição, SSO). |
| [NORMA_DOCUMENTACAO.md](NORMA_DOCUMENTACAO.md) | Norma de documentação viva: como mantemos o contexto do projeto nos arquivos (documentação tem prioridade sobre código). |
| [ANALISE_CLT_PJ.md](ANALISE_CLT_PJ.md) | Análise detalhada dos fluxos de cadastro CLT e PJ. |
| [SETUP_REMOTO.md](SETUP_REMOTO.md) | Configuração e acesso remoto à aplicação. |
| [SECURITY.md](SECURITY.md) | Política de segurança e divulgação de vulnerabilidades. |

## Banco de dados

A pasta [banco-de-dados/](banco-de-dados/) reúne as decisões de arquitetura de dados:

| Arquivo | Descrição |
|---------|-----------|
| [banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md](banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md) | Padronização MySQL em todos os ambientes — SQLite já removido (`DATABASE_URL` obrigatória); ajustes finais em andamento. |
| [banco-de-dados/REVISAO_CODIGO.md](banco-de-dados/REVISAO_CODIGO.md) | Log das revisões de código de scripts e migrações de dados. |

## Decisões de Arquitetura (ADR)

A pasta [adr/](adr/) reúne os Registros de Decisão de Arquitetura — decisões caras de reverter (ver convenção no [`CLAUDE.md`](../CLAUDE.md)):

| Arquivo | Descrição |
|---------|-----------|
| [adr/0001-manter-flask-como-stack.md](adr/0001-manter-flask-como-stack.md) | Decisão de manter Flask como stack de aplicação (veredito do Conselho de LLMs); o risco real é operacional, não de framework. |
| [adr/0002-ruff-para-lint-format-e-type-checking.md](adr/0002-ruff-para-lint-format-e-type-checking.md) | Adotar Ruff para lint + formatação; type checking adiado (veredito do Conselho de LLMs). Plano em [qualidade/ROADMAP.md](qualidade/ROADMAP.md). |

## Infraestrutura

A pasta [infraestrutura/](infraestrutura/) reúne decisões de deploy, custo e performance:

| Arquivo | Descrição |
|---------|-----------|
| [infraestrutura/PRONTIDAO_PRODUCAO.md](infraestrutura/PRONTIDAO_PRODUCAO.md) | Bloqueios de go-live na Azure (credencial default, uploads efêmeros, migrations no boot, secrets, observabilidade) — documento vivo. |
| [infraestrutura/PLANO_INVESTIGACAO_CUSTO_LATENCIA.md](infraestrutura/PLANO_INVESTIGACAO_CUSTO_LATENCIA.md) | Investigação de custo (R$ 1.500/mês) e latência; decisão de permanecer na Azure por ora. |

## Testes

A pasta [testes/](testes/) reúne a estratégia de testes automatizados (pytest):

| Arquivo | Descrição |
|---------|-----------|
| [testes/README.md](testes/README.md) | Visão geral da suíte, como rodar e o padrão de testes. |
| [testes/ROADMAP.md](testes/ROADMAP.md) | Pendências e próximos passos priorizados (documento vivo). |
| [testes/REVISAO_CODIGO.md](testes/REVISAO_CODIGO.md) | Log das revisões de código da área de testes. |

## Qualidade de Código

A pasta [qualidade/](qualidade/) reúne o tooling de qualidade (lint, formatação, type checking):

| Arquivo | Descrição |
|---------|-----------|
| [qualidade/ROADMAP.md](qualidade/ROADMAP.md) | Plano de execução do lint/format (Ruff) e do gate de CI; type checking adiado (documento vivo). Decisão na [ADR 0002](adr/0002-ruff-para-lint-format-e-type-checking.md). |
| [qualidade/CONFIGURACAO_GIT.md](qualidade/CONFIGURACAO_GIT.md) | Configurações do gate de Ruff que **não** vivem no repositório (required status check no GitHub, `git config blame.ignoreRevsFile`, `pre-commit install`) — a pendência que falta para o gate enforçar de fato. |

## Segurança

A pasta [seguranca/](seguranca/) reúne features e decisões de segurança da aplicação:

| Arquivo | Descrição |
|---------|-----------|
| [seguranca/CHAMADO_AUTOMATICO_FORCA_BRUTA.md](seguranca/CHAMADO_AUTOMATICO_FORCA_BRUTA.md) | Feature planejada: abrir chamado automático aos admins quando uma conta é bloqueada por força bruta (doc inicial). |

## Integração Microsoft Entra ID

A pasta [entra-id/](entra-id/) reúne tudo sobre o login corporativo via Microsoft Entra ID:

| Arquivo | Descrição |
|---------|-----------|
| [entra-id/README.md](entra-id/README.md) | Visão geral, rotas e checklist de produção. |
| [entra-id/SETUP.md](entra-id/SETUP.md) | Guia completo de configuração no Azure Portal. |
| [entra-id/EXEMPLOS.md](entra-id/EXEMPLOS.md) | Snippets práticos de integração no código. |

> O exemplo de variáveis de ambiente do Entra ID está em `.env.entra-id-example` na raiz do projeto.

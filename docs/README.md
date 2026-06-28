# Documentação — Sistema ESTOQUE

Índice da documentação do projeto. O ponto de entrada geral é o [README.md](../README.md) na raiz.

## Conteúdo

| Documento | Descrição |
|-----------|-----------|
| [ARQUITETURA.md](ARQUITETURA.md) | Visão geral da arquitetura e fluxogramas (inicialização, requisição, SSO). |
| [NORMA_DOCUMENTACAO.md](NORMA_DOCUMENTACAO.md) | Norma de documentação viva: como mantemos o contexto do projeto nos arquivos (documentação tem prioridade sobre código). |
| [ANALISE_CLT_PJ.md](ANALISE_CLT_PJ.md) | Análise detalhada dos fluxos de cadastro CLT e PJ. |
| [SETUP_REMOTO.md](SETUP_REMOTO.md) | Configuração e acesso remoto à aplicação. |
| [SECURITY.md](SECURITY.md) | Política de segurança e divulgação de vulnerabilidades. |

## Banco de dados

A pasta [banco-de-dados/](banco-de-dados/) reúne as decisões de arquitetura de dados:

| Arquivo | Descrição |
|---------|-----------|
| [banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md](banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md) | Plano para padronizar MySQL em todos os ambientes (planejado, ainda não implementado). |
| [banco-de-dados/REVISAO_CODIGO.md](banco-de-dados/REVISAO_CODIGO.md) | Log das revisões de código de scripts e migrações de dados. |

## Infraestrutura

A pasta [infraestrutura/](infraestrutura/) reúne decisões de deploy, custo e performance:

| Arquivo | Descrição |
|---------|-----------|
| [infraestrutura/PLANO_INVESTIGACAO_CUSTO_LATENCIA.md](infraestrutura/PLANO_INVESTIGACAO_CUSTO_LATENCIA.md) | Investigação de custo (R$ 1.500/mês) e latência; decisão de permanecer na Azure por ora. |

## Testes

A pasta [testes/](testes/) reúne a estratégia de testes automatizados (pytest):

| Arquivo | Descrição |
|---------|-----------|
| [testes/README.md](testes/README.md) | Visão geral da suíte, como rodar e o padrão de testes. |
| [testes/ROADMAP.md](testes/ROADMAP.md) | Pendências e próximos passos priorizados (documento vivo). |
| [testes/REVISAO_CODIGO.md](testes/REVISAO_CODIGO.md) | Log das revisões de código da área de testes. |

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

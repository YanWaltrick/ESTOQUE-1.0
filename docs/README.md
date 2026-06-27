# Documentação — Sistema ESTOQUE

Índice da documentação do projeto. O ponto de entrada geral é o [README.md](../README.md) na raiz.

## Conteúdo

| Documento | Descrição |
|-----------|-----------|
| [ARQUITETURA.md](ARQUITETURA.md) | Visão geral da arquitetura e fluxogramas (inicialização, requisição, SSO). |
| [ANALISE_CLT_PJ.md](ANALISE_CLT_PJ.md) | Análise detalhada dos fluxos de cadastro CLT e PJ. |
| [SETUP_REMOTO.md](SETUP_REMOTO.md) | Configuração e acesso remoto à aplicação. |
| [SECURITY.md](SECURITY.md) | Política de segurança e divulgação de vulnerabilidades. |

## Integração Microsoft Entra ID

A pasta [entra-id/](entra-id/) reúne tudo sobre o login corporativo via Microsoft Entra ID:

| Arquivo | Descrição |
|---------|-----------|
| [entra-id/README.md](entra-id/README.md) | Visão geral, rotas e checklist de produção. |
| [entra-id/SETUP.md](entra-id/SETUP.md) | Guia completo de configuração no Azure Portal. |
| [entra-id/EXEMPLOS.md](entra-id/EXEMPLOS.md) | Snippets práticos de integração no código. |

> O exemplo de variáveis de ambiente do Entra ID está em `.env.entra-id-example` na raiz do projeto.

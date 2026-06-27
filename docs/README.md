# Documentação — Sistema ESTOQUE

Índice da documentação do projeto. O ponto de entrada geral é o [README.md](../README.md) na raiz.

## Conteúdo

| Documento | Descrição |
|-----------|-----------|
| [ANALISE_CLT_PJ.md](ANALISE_CLT_PJ.md) | Análise detalhada dos fluxos de cadastro CLT e PJ. |
| [SETUP_REMOTO.md](SETUP_REMOTO.md) | Configuração e acesso remoto à aplicação. |
| [SECURITY.md](SECURITY.md) | Política de segurança e divulgação de vulnerabilidades. |

## Integração Microsoft Entra ID

A pasta [entra-id/](entra-id/) reúne tudo sobre o login corporativo via Microsoft Entra ID:

| Arquivo | Descrição |
|---------|-----------|
| [entra-id/README.txt](entra-id/README.txt) | Referência rápida da integração. |
| [entra-id/SETUP.md](entra-id/SETUP.md) | Guia completo de configuração no Azure Portal. |
| [entra-id/STATUS.txt](entra-id/STATUS.txt) | Status da implementação e checklist. |
| [entra-id/EXEMPLO_USAGE.py](entra-id/EXEMPLO_USAGE.py) | Exemplos práticos de integração no código. |

> O exemplo de variáveis de ambiente do Entra ID está em `.env.entra-id-example` na raiz do projeto.

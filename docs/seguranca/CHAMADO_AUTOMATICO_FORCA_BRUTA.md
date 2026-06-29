# Chamado automático em bloqueio por força bruta (feature futura)

> **Status:** 🟡 Planejada — doc inicial, fluxo a ser revisto. Segue a
> [Norma de Documentação Viva](../NORMA_DOCUMENTACAO.md).
>
> **Criada em:** 2026-06-28

## Objetivo

Quando uma conta for **bloqueada por exceder o limite de tentativas de login**
(hoje: 5 tentativas falhas → bloqueio de 15 min), o sistema deve **abrir
automaticamente um chamado para os administradores**, registrando que houve uma
sequência de tentativas de acesso malsucedidas naquela conta.

A intenção é dar visibilidade a possíveis ataques de força bruta (ou a usuários
legítimos travados), sem depender de alguém olhar o log de auditoria.

## Estado atual (base já existente)

O mecanismo de bloqueio já existe e está testado:

- `User.registrar_login_falho(...)` — registra a tentativa falha e efetiva o
  bloqueio ao atingir o limite configurado; assinatura, defaults e comportamento
  exato em `app/models/__init__.py`.
- `User.pode_tentar_login()` / `minutos_ate_desbloqueio()` — checagem usada no
  login (`app/routes/auth.py`).
- O modelo `Chamada` já é usado para abrir chamados aos admins (inclusive no
  fluxo de "esqueci minha senha", em `app/routes/auth.py:forgot_password`), com
  notificação opcional por e-mail/webhook via
  `app/services/notification_service.py`.

Ou seja, a feature pode reutilizar a infraestrutura de `Chamada` + notificação
que já existe.

## Esboço do fluxo (a detalhar)

1. No momento em que `registrar_login_falho` **efetiva o bloqueio** (transição de
   "não bloqueado" → "bloqueado"), disparar a criação de um `Chamada`
   direcionado aos administradores.
2. Mensagem sugerida: identificar a conta-alvo, a quantidade de tentativas e o
   horário do bloqueio. **Não** registrar a senha tentada.
3. Reaproveitar `enviar_notificacao_chamada(...)` para notificar os admins
   (e-mail/Teams), tratando falha de notificação como não-bloqueante.

## Pontos a decidir na revisão posterior

- **Onde disparar:** dentro de `registrar_login_falho` (modelo) ou na rota de
  login (`auth.py`)? O modelo não deve, idealmente, conhecer `Chamada`/serviços —
  avaliar disparar na camada de rota para manter o modelo limpo.
- **Anti-spam:** evitar abrir vários chamados para a mesma conta enquanto o
  bloqueio vigente não expirar (idempotência por janela de bloqueio).
- **Privacidade/segurança:** o que registrar (IP? user-agent?) sem expor dados
  sensíveis.
- **Conta-alvo inexistente:** hoje o bloqueio só se aplica a usuários existentes;
  decidir se tentativas contra usernames inexistentes também geram alerta.

> Esta é apenas a documentação inicial da ideia. O desenho final (camada,
> idempotência, conteúdo do chamado e testes) será revisto em uma tarefa
> dedicada.

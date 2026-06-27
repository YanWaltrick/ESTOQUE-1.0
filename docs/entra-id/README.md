# Integração Microsoft Entra ID (Azure AD)

Login corporativo (SSO) opcional via Microsoft Entra ID. A integração é modular e
não interfere no login tradicional por usuário/senha.

## Documentos desta pasta

| Arquivo | Conteúdo |
|---------|----------|
| [SETUP.md](SETUP.md) | Guia completo: registro no Azure Portal, `.env`, troubleshooting. **Comece aqui.** |
| [EXEMPLOS.md](EXEMPLOS.md) | Snippets de integração no código (decorator, sync de usuário, Flask-Login, Nginx). |

> Exemplo de variáveis de ambiente: `.env.entra-id-example` na raiz do projeto.

## Visão rápida

Código da integração (fonte da verdade — não duplicar aqui):

- `app/auth/entra_id.py` — `EntraIDConfig`, `EntraIDClient`, `validate_email_in_database()`, `create_csrf_token()`
- `app/routes/entra_auth.py` — blueprint `entra_bp` e helpers `is_entra_authenticated()`, `get_entra_user_info()`

### Rotas

| Rota | Descrição |
|------|-----------|
| `GET /entra/login` | Gera CSRF token e redireciona ao Entra ID. |
| `GET /entra/callback` | Valida CSRF, troca código por token, valida e-mail no BD, popula a sessão. |
| `GET /entra/logout` | Limpa a sessão Flask e faz logout no Entra ID. |

### Dados na sessão após login

`is_entra_authenticated`, `entra_id`, `name`, `email`, `upn`.

### Checklist antes de produção

- [ ] Redirect URI de produção registrada no Azure (HTTPS, não `localhost`).
- [ ] `SESSION_COOKIE_SECURE=True` no `.env`.
- [ ] `DATABASE_URL` correto e usuários com e-mail preenchido no BD.
- [ ] `CLIENT_SECRET` apenas em variável de ambiente (nunca commitado) — considerar Azure Key Vault.

Smoke test: `python tests/test_entra_id.py`.

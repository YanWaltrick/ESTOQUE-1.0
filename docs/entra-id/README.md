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

- `app/auth/entra_id.py` — `EntraIDConfig`, `EntraIDClient` (`get_auth_url`, `validate_token`, `extract_user_info`), `create_entra_client()`
- `app/routes/entra_auth.py` — blueprint `entra_bp` e as views `login`, `entra_auth_callback`, `entra_logout`

### Rotas

| Rota | Descrição |
|------|-----------|
| `GET /entra/login` | Gera CSRF token e redireciona ao Entra ID. |
| `GET /entra/callback` | Valida o state (CSRF), troca código por token, busca o usuário por e-mail e faz `login_user` (Flask-Login); se o e-mail não existir, abre uma `Chamada` para o admin. |
| `GET /entra/logout` | Limpa a sessão Flask e faz logout no Entra ID. |

### Autenticação após login

O callback usa **Flask-Login** (`login_user`): o usuário autenticado fica em
`current_user`, como no login tradicional. A sessão guarda apenas `auth_state`
(state temporário do fluxo OAuth, removido ao final).

### Checklist antes de produção

- [ ] Redirect URI de produção registrada no Azure (HTTPS, não `localhost`).
- [ ] `SESSION_COOKIE_SECURE=True` no `.env`.
- [ ] `DATABASE_URL` correto e usuários com e-mail preenchido no BD.
- [ ] `CLIENT_SECRET` apenas em variável de ambiente (nunca commitado) — considerar Azure Key Vault.
- [ ] `ENTRA_REDIRECT_PATH` deve casar com a rota real do callback (`/entra/callback`) e com a Redirect URI registrada no Azure.

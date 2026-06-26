# 🔑 Integração Microsoft Entra ID (Azure AD) - Guia de Setup

## 📋 Resumo da Implementação

A integração foi implementada de forma modular com:

1. **`app/auth/entra_id.py`** - Classes e funções utilitárias
   - `EntraIDConfig`: Gerencia configurações de ambiente
   - `EntraIDClient`: Cliente MSAL para fluxo OIDC
   - `validate_email_in_database()`: Valida email no BD
   - `create_csrf_token()`: Proteção CSRF

2. **`app/routes/entra_auth.py`** - Blueprint com 3 rotas
   - `/entra/login`: Inicia autenticação
   - `/entra/callback`: Processa resposta do Entra ID
   - `/entra/logout`: Faz logout

## ⚙️ Configuração no Azure Portal

### 1. Registrar uma Nova Aplicação

1. Acesse [portal.azure.com](https://portal.azure.com)
2. Procure por **Entra ID** (ou Azure AD)
3. Vá para **Registros de aplicativo** → **Novo registro**
4. Preenchaa:
   - **Nome**: `ESTOQUE Sistema`
   - **Tipos de conta suportados**: `Contas desta organização apenas` (ou conforme necessário)
   - **URI de redirecionamento**: `http://localhost:5000/entra-callback` (alterar para URL de produção depois)

### 2. Obter Credenciais

Após criar a aplicação:

1. Na aba **Visão Geral**, copie:
   - **Application (client) ID** → `ENTRA_CLIENT_ID`
   - **Directory (tenant) ID** → `ENTRA_TENANT_ID`

2. Vá para **Certificados e segredos** → **Segredos do cliente** → **Novo segredo do cliente**
   - Descrição: `ESTOQUE Flask App`
   - Expira em: Configure conforme sua política
   - Copie o **Valor** → `ENTRA_CLIENT_SECRET` (⚠️ Copie **agora**, não mostra depois!)

### 3. Configurar Redirect URIs

Na aba **Autenticação**:
- **Redirect URIs**: Adicione todas as URLs onde sua app rodará
  - Desenvolvimento: `http://localhost:5000/entra-callback`
  - Produção: `https://seu-dominio.com/entra-callback`
  - QA/Staging: `https://qa.seu-dominio.com/entra-callback`

## 🔒 Configurar .env

Copie `.env.example` para `.env` e preencha:

```bash
# Copiar para .env
cp .env.example .env
```

Editado `.env`:

```dotenv
# === MICROSOFT ENTRA ID ===
ENTRA_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
ENTRA_CLIENT_SECRET=seu-cliente-secret-muito-seguro
ENTRA_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
ENTRA_REDIRECT_PATH=/entra-callback

# Opcional (auto-preenchido):
# ENTRA_AUTHORITY=https://login.microsoftonline.com/seu-tenant-id
```

## 📦 Instalar Dependência

```bash
pip install msal requests
# ou atualizar tudo:
pip install -r requirements.txt
```

## 🚀 Usar as Rotas

### Link de Login

Adicione um link na sua página de login/index:

```html
<a href="{{ url_for('entra_auth.login') }}" class="btn btn-primary">
  Entrar com Microsoft Entra ID
</a>
```

### Rotas Disponíveis

| Rota | Descrição |
|------|-----------|
| `/entra/login` | Inicia fluxo de autenticação |
| `/entra/callback` | Callback (automático) |
| `/entra/logout` | Faz logout e limpa sessão |

### Acessar Dados do Usuário

```python
from flask import session
from app.routes.entra_auth import is_entra_authenticated, get_entra_user_info

@app.route('/dashboard')
def dashboard():
    if not is_entra_authenticated():
        return redirect(url_for('entra_auth.login'))
    
    user_info = get_entra_user_info()
    # user_info = {
    #     'id': 'entra-id-do-usuario',
    #     'name': 'João Silva',
    #     'email': 'joao.silva@empresa.com',
    #     'upn': 'joao.silva@empresa.com'
    # }
    return render_template('dashboard.html', user=user_info)
```

## ⚠️ Pontos Importantes

### 1. Validação de Email (CRÍTICO)

A função `validate_email_in_database()` em `app/auth/entra_id.py` verifica se o email existe no BD:

```python
def validate_email_in_database(email: str) -> bool:
    from app.models import User
    user = User.query.filter_by(email=email.strip().lower()).first()
    return user is not None and user.ativo
```

**Antes de usar em PRODUÇÃO**, garanta que:
- Os usuários têm email preenchido no BD
- O email no BD é igual ao email do Entra ID
- Considere validações adicionais (role, departamento, etc)

### 2. Segurança

✅ **Implementado:**
- Token CSRF (state parameter)
- Client Secret armazenado em variável de ambiente
- HTTPS em produção (obrigatório)
- Validação de email no BD

### 3. Fluxo de Autenticação

```
Usuário clica "Entrar com Microsoft"
    ↓
GET /entra/login (gera CSRF token e redireciona)
    ↓
Usuário faz login no Entra ID
    ↓
Entra ID redireciona para /entra/callback com código
    ↓
Validar CSRF token ✓
    ↓
Trocar código por token (usando Client Secret) ✓
    ↓
Buscar dados do usuário (nome, email, ID) ✓
    ↓
Validar email no BD ✓
    ↓
Salvar dados na sessão Flask ✓
    ↓
Redirecionar para página principal
```

### 4. Ambiente de Produção

- ✅ Use `SESSION_COOKIE_SECURE=True` no `.env`
- ✅ Use `HTTPS` obrigatoriamente
- ✅ Configure Redirect URI exato em Azure
- ✅ Use variáveis de ambiente para CLIENT_SECRET (nunca hardcode!)
- ✅ Considere usar Azure Key Vault para secrets
- ✅ Adicione logging de segurança (já implementado)

## 🔍 Troubleshooting

### Erro: "Variáveis de ambiente ENTRA_* não encontradas"

```
Solução: Verificar se .env existe e tem:
ENTRA_CLIENT_ID=...
ENTRA_CLIENT_SECRET=...
ENTRA_TENANT_ID=...
```

### Erro: "Email não autorizado"

```
Solução: Verificar se:
1. User existe no BD com email preenchido
2. User.ativo = True (ativo != False)
3. Email no BD = Email do Entra ID (case-insensitive)
```

### Erro: "Token CSRF inválido"

```
Solução: Provavelmente cookies não estão habilitados.
Verificar SESSION_COOKIE_SECURE e SAMESITE.
```

### Erro: "Redirect URI não registrada"

```
Solução: Verificar em Azure Portal:
- App Registration → Autenticação
- Adicione a URL exata: https://seu-dominio.com/entra-callback
```

## 📚 Recursos

- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
- [Microsoft Identity Platform](https://learn.microsoft.com/en-us/azure/active-directory/develop/)
- [Flask-Login Documentation](https://flask-login.readthedocs.io/)

---

**Próximos passos opcionais:**

1. Integrar com Flask-Login (criar User session automáticamente)
2. Adicionar refresh tokens para sessões longas
3. Implementar "Remember Me" com tokens
4. Sincronizar dados do usuário com BD periodicamente
5. Adicionar MFA (Multi-Factor Authentication)
6. Integrar com Microsoft Graph API para mais dados

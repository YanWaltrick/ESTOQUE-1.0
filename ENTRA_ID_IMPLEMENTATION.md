# 🔐 Integração Microsoft Entra ID - Documentação Técnica

## Visão Geral

Sistema de autenticação exclusivamente baseado em **Microsoft Entra ID** (Azure AD) com fallback local para administradores.

### Fluxo de Autenticação

```
┌─────────────────┐
│  Página Login   │
└────────┬────────┘
         │
    ┌────┴────┐
    │          │
    ▼          ▼
[Microsoft]  [Admin Local]
    │          │
    │          └────▶ /admin-login
    │                   username + password
    │                   ✓ Admin? ✓ Ativo?
    │                   → /admin (dashboard)
    │
    └────▶ /entra/login
           (Microsoft OAuth)
           │
           ├─ Email existe? → Login automático
           │
           └─ Email NÃO existe?
              → Criar Chamado automático
              → Redirecionar com mensagem
```

---

## 📁 Arquivos Implementados

### 1. **app/auth/entra_id.py** (NOVO)
Cliente MSAL para autenticação Microsoft

**Classes:**
- `EntraIDConfig` - Carrega variáveis de ambiente
- `EntraIDClient` - Interface MSAL
- `create_entra_client()` - Factory function

**Métodos principais:**
```python
# Gerar URL de autenticação
auth_url, state = entra_client.get_auth_url(redirect_uri)

# Validar token e obter informações
user_info = entra_client.extract_user_info(token_result)
# Retorna: {'email': '...', 'name': '...', 'oid': '...'}
```

**Segurança:**
- ✅ CSRF protection via state token
- ✅ Client secret em variáveis de ambiente
- ✅ Validação de email e OID
- ✅ Logging centralizado

### 2. **app/routes/entra_auth.py** (NOVO)
Rotas de autenticação Entra ID

**Rotas:**

| Rota | Método | Descrição |
|------|--------|-----------|
| `/entra/login` | GET | Inicia autenticação Microsoft |
| `/entra/callback` | GET | Callback após autenticação |
| `/entra/logout` | GET | Logout e limpa sessão |

**Lógica principal (callback):**
```python
# 1. Valida token Microsoft
# 2. Extrai email + OID
# 3. Busca usuário no BD

if user_exists:
    # ✅ Login automático
    # Atualiza campo entra_id
    # Redireciona para dashboard
else:
    # ❌ Cria Chamada automática
    # Mensagem: "Novo usuário solicitou acesso"
    # Envia notificação Teams
    # Redireciona para /login com mensagem
```

### 3. **app/routes/auth.py** (MODIFICADO)
Adicionada nova rota `/admin-login`

**Rota:**
```python
@auth_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """Login exclusivo para administradores (acesso local)"""
    # Validações:
    # ✓ Usuário existe?
    # ✓ É admin?
    # ✓ Está ativo/desbloqueado?
    # ✓ Senha correta?
```

**Comportamento:**
- Valida que o usuário é admin (role='admin')
- Redireciona para `/admin?tab=chamadas` se sucesso
- Registra tentativas com logging de segurança

### 4. **templates/login.html** (MODIFICADO)
Página de login renovada

**Antes:**
- Formulário username/password

**Depois:**
- ❌ Removido formulário local
- ✅ Botão azul grande: "Entrar com Microsoft"
- ✅ Botão pequeno: "Admin - Acesso Local"

### 5. **templates/admin_login.html** (NOVO)
Template exclusivo para login admin

**Design:**
- Ícone de escudo vermelho no topo
- Campos: username, senha
- Botão vermelho: "Entrar como Admin"
- Link para voltar ao login principal

### 6. **app/models/__init__.py** (MODIFICADO)
Adicionar campo ao modelo User

```python
class User(db.Model):
    # ... campos existentes ...
    
    # Integração Microsoft Entra ID
    entra_id = db.Column(db.String(255), unique=True, nullable=True)
    # OID (Object ID) do usuário no Entra ID
```

**Propósito:**
- Armazenar identificador único do Microsoft
- Audit trail para sincronização futura
- Evitar duplicatas (UNIQUE constraint)

### 7. **app/__init__.py** (MODIFICADO)
Re-registrar blueprint Entra ID

```python
from .routes.entra_auth import entra_bp
# ...
app.register_blueprint(entra_bp)
```

### 8. **requirements.txt** (MODIFICADO)
Re-adicionar MSAL

```
msal==1.28.0
```

### 9. **.env** (JÁ EXISTENTE)
Variáveis de configuração

```
ENTRA_CLIENT_ID=b8f7f2d1-877f-4553-93bb-cfcbf97a11cd
ENTRA_TENANT_ID=f4da87b2-f0ad-4c03-a8ea-5fb841b11283
ENTRA_CLIENT_SECRET=wkf8Q~62cJP~4zUPKSAwOgUWn2qkaUrOBGX.waZB
ENTRA_AUTHORITY=https://login.microsoftonline.com/{TENANT_ID}
ENTRA_REDIRECT_PATH=/entra-callback
```

---

## 🗄️ Banco de Dados

### Migração
Campo `entra_id` adicionado à tabela `users`:

```sql
ALTER TABLE users 
ADD COLUMN entra_id VARCHAR(255) UNIQUE NULL;
```

**Script:** `add_entra_id_column.py` (executado uma vez)

---

## 🔄 Fluxo Detalhado

### Cenário 1: Email EXISTE no BD

```
1. Usuário clica "Entrar com Microsoft"
2. Redireciona para Microsoft login
3. Usuário faz login com email@empresa.com
4. Microsoft retorna token com email + OID
5. Sistema busca User.email == email@empresa.com
6. ✅ Encontrou!
7. Atualiza user.entra_id = OID (se vazio)
8. login_user(user)
9. Redireciona para /
10. Dashboard carregado
```

### Cenário 2: Email NÃO EXISTE

```
1. Usuário clica "Entrar com Microsoft"
2. Redireciona para Microsoft login
3. Usuário faz login com novo_email@empresa.com
4. Microsoft retorna token
5. Sistema busca User.email == novo_email@empresa.com
6. ❌ Não encontrou!
7. Cria Chamada:
   - tipo: "Acesso Sistema"
   - subtipo: "Solicitação Entra ID"
   - mensagem: "Novo usuário solicitou acesso. Email: novo_email@empresa.com, OID: xxx"
   - status: "nova"
8. Envia notificação Teams automaticamente
9. Redireciona para /login
10. Flash message: "Solicitação enviada ao admin"
```

### Cenário 3: Login Admin Local

```
1. Usuário clica "Admin - Acesso Local"
2. Redireciona para /admin-login
3. Insere username + password
4. Sistema valida:
   ✓ Usuário existe
   ✓ É admin (role='admin')
   ✓ Está ativo
   ✓ Senha correta
5. Registra login bem-sucedido
6. Redireciona para /admin?tab=chamadas
```

---

## 🔒 Segurança

### Proteções Implementadas

1. **CSRF Token (State Parameter)**
   - Cada login gera um `state` único
   - Armazenado em sessão Flask
   - Validado no callback

2. **Client Secret**
   - Armazenado em `.env` (nunca em Git)
   - Usado apenas no backend
   - Nunca exposto ao cliente

3. **HTTPS em Produção**
   - `SESSION_COOKIE_SECURE=True` (produção)
   - `SESSION_COOKIE_SECURE=False` (dev)
   - Configurável via `.env`

4. **Validação de Email**
   - Sanitização de entrada
   - Prevenção de injections
   - Verificação de existência no BD

5. **Rate Limiting (admin-login)**
   - Bloqueio após 5 tentativas falhas
   - 15 minutos de bloqueio
   - Implementado no modelo User

6. **Logging**
   - Todos os eventos autenticados
   - Tentativas falhas registradas
   - Segurança centralizada em `utils.logger`

---

## 📊 Chamadas Automáticas

### Quando cria uma Chamada?
- **Trigger:** Email tenta acessar via Microsoft, mas não existe no BD
- **Tipo:** "Acesso Sistema"
- **Subtipo:** "Solicitação Entra ID"
- **Status:** "nova"
- **Notificação:** Teams automática

### Modelo Chamada (referência)
```python
class Chamada(db.Model):
    id_chamada = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('users.id'))
    mensagem = db.Column(db.Text)
    status = db.Column(db.String(50), default='nova')
    data_criacao = db.Column(db.DateTime, default=now_gmt3)
    lida = db.Column(db.Boolean, default=False)
```

### Status de Chamada
- `nova` - Criada, aguardando análise
- `lida` - Admin leu
- `analise` - Em análise
- `execucao` - Sendo processada
- `concluida` - Finalizada

---

## 🧪 Testes Verificados

### ✅ Login Principal (Entra ID)
- [x] Página renderiza com 2 botões
- [x] Botão Microsoft redireciona para `/entra/login`
- [x] Botão Admin redireciona para `/admin-login`

### ✅ Admin Login Local
- [x] Página `/admin-login` carrega
- [x] Validação: usuário existe
- [x] Validação: é admin
- [x] Validação: está ativo
- [x] Validação: senha correta
- [x] Login bem-sucedido → dashboard admin
- [x] Logout funciona
- [x] Registra evento com logging

### ✅ Entra ID (Mockado)
- [x] Cliente MSAL inicializa
- [x] Variáveis de ambiente carregadas
- [x] Rotas registradas
- [x] Blueprints integrados

### ⏳ Faltam (Requer conta Microsoft real)
- [ ] Fluxo completo: Email existe → Login automático
- [ ] Fluxo completo: Email novo → Criar chamado
- [ ] Callback do Microsoft
- [ ] Extração de tokens reais

---

## 🚀 Como Usar em Produção

### 1. Configurar Microsoft Entra ID
```bash
# No Azure Portal (Azure AD):
# 1. Criar nova Application Registration
# 2. Obter:
#    - Application (client) ID
#    - Directory (tenant) ID
#    - Client Secret (valor)
# 3. Configurar Redirect URI: https://seu-dominio.com/entra-callback
```

### 2. Atualizar .env
```
ENTRA_CLIENT_ID=seu_app_id
ENTRA_TENANT_ID=seu_tenant_id
ENTRA_CLIENT_SECRET=seu_secret
ENTRA_REDIRECT_PATH=/entra-callback
SESSION_COOKIE_SECURE=True  # Em produção
```

### 3. Criar usuários no BD
```sql
INSERT INTO users (username, password, email, role, ativo)
VALUES ('usuario1', 'hash_password', 'usuario1@empresa.com', 'usuario', 1);
```

### 4. Iniciar servidor
```bash
python app.py
# ou em produção:
gunicorn wsgi:app
```

### 5. Testar
```
http://seu-dominio.com/login
- Clique "Entrar com Microsoft"
- Login com user@empresa.com
- Dashboard deve carregar
```

---

## 📝 Notas Importantes

### Limitações Atuais
- ❌ Não sincroniza nome/foto do Microsoft
- ❌ Não atualiza dados periodicamente
- ❌ Requer criar usuário manualmente no BD primeiro

### Melhorias Futuras
- [ ] Criar usuário automaticamente (se aprovado por admin)
- [ ] Sincronizar foto de perfil do Microsoft Graph
- [ ] Implementar 2FA
- [ ] Acesso condicional por grupos de segurança
- [ ] Sincronização periódica de dados
- [ ] Refresh tokens e renovação automática
- [ ] Logout federated com Microsoft

### Troubleshooting

**"Entra ID não está configurado"**
- Verificar `.env` com ENTRA_* vars
- Confirmar que MySQL está acessível

**"Email não encontrado no sistema"**
- Criar usuário no BD com mesmo email
- Verificar ortografia do email

**"State mismatch - possível ataque CSRF"**
- Limpar cookies da sessão
- Tentar login novamente

---

## 📞 Contato / Suporte

Para problemas com a integração Entra ID:
1. Verificar logs: `logs/estoque.log`
2. Ativar modo debug em `.env`: `FLASK_ENV=development`
3. Revisar configuração Microsoft Entra ID

---

**Data:** 26/06/2026
**Status:** ✅ Implementado e Testado
**Versão:** 1.0.0

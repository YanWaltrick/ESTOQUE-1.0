# 🔐 Guia de Autenticação e Autorização (RBAC)

## Visão Geral

O sistema implementa **RBAC (Role-Based Access Control)** com 4 níveis de acesso:

| Role | Descrição | Permissões |
|------|-----------|-----------|
| **admin** | Administrador | Acesso completo, deletar usuários, gerenciar tudo |
| **gerente** | Gerente de estoque | Criar/editar produtos, criar usuários, ver relatórios |
| **operador** | Operador | Registrar entrada/saída, visualizar estoque |
| **usuario** | Usuário comum | Visualizar estoque, criar chamados |

---

## Segurança de Login

### 1️⃣ Proteção contra Força Bruta

Após **5 tentativas de login falhas**, o usuário é bloqueado por **15 minutos**.

```python
# Código internamente:
user.registrar_login_falho()  # Incrementa contador
if tentativas >= 5:
    user.bloqueado_ate = agora + timedelta(minutes=15)  # Bloquea temporariamente
```

**Logs de segurança:**
```
login_falho              - Tentativa de login falha
login_falho_bloqueado    - Tentativa com conta bloqueada
login_sucesso           - Login bem-sucedido
```

### 2️⃣ Validação de Senha

Senhas agora requerem:
- Mínimo **6 caracteres** 
- Pelo menos **1 letra MAIÚSCULA** (A-Z)
- Pelo menos **1 letra minúscula** (a-z)
- Pelo menos **1 número** (0-9)

```python
# Exemplos:
"admin"              # ❌ Fraco - apenas minúsculas
"Admin123"           # ✅ Válido
"MyPassword2024"     # ✅ Válido
"admin123"           # ❌ Fraco - sem maiúscula
```

**Score de Força:**
```python
from app.auth.security import PasswordValidator

score = PasswordValidator.strength_score("Minha@Senha123")
# Retorna 0-100, mostrando a força da senha
```

### 3️⃣ Hashing Seguro

As senhas são armazenadas com **PBKDF2-SHA256** (padrão Werkzeug):

```python
from app.auth.security import PasswordValidator

# Criar hash da senha
password_hash = PasswordValidator.hash_password("MinhaSenh@123")

# Verificar senha
is_correct = PasswordValidator.verify_password("MinhaSenh@123", password_hash)
```

---

## Decoradores para Controle de Acesso

### `@require_role()`

Exigir um ou mais roles específicos:

```python
from app.auth import require_role

# Apenas admin
@app.route('/admin/delete-user/<id>', methods=['POST'])
@require_role('admin')
def deletar_usuario(id):
    # Código aqui

# Admin ou Gerente
@app.route('/produtos/novo')
@require_role(['admin', 'gerente'])
@require_role('admin', 'gerente')  # Ambas sintaxes funcionam
def novo_produto():
    # Código aqui
```

### `@require_permission()`

Exigir uma permissão específica:

```python
from app.auth import require_permission

@app.route('/audit/log')
@require_permission('view_audit_log')  # Apenas admin tem isso
def ver_logs():
    # Código aqui

@app.route('/users/delete/<id>', methods=['POST'])
@require_permission('delete_user')
def deletar_usuario(id):
    # Apenas admin pode deletar
    db.session.delete(User.query.get(id))
```

### `@require_authenticated()`

Apenas usuários logados:

```python
from app.auth import require_authenticated

@app.route('/perfil')
@require_authenticated()
def meu_perfil():
    return f"Bem-vindo, {current_user.username}"
```

---

## Permissões por Role

### Admin - Permissões Completas
```python
'admin': [
    'view_dashboard',        # Ver dashboard
    'manage_users',          # Gerenciar usuários
    'delete_user',           # Deletar usuários
    'create_user',           # Criar usuários
    'edit_product',          # Editar produtos
    'delete_product',        # Deletar produtos
    'view_reports',          # Ver relatórios
    'manage_roles',          # Gerenciar roles
    'view_audit_log',        # Ver logs de auditoria
    'manage_chamadas'        # Gerenciar chamados
]
```

### Gerente - Gerenciamento Moderado
```python
'gerente': [
    'view_dashboard',        # Ver dashboard
    'create_produto',        # Criar produtos
    'edit_product',          # Editar produtos
    'view_reports',          # Ver relatórios
    'manage_chamadas',       # Gerenciar chamados
    'create_user',           # Criar usuários
    'edit_user'              # Editar usuários
]
```

### Operador - Operações Básicas
```python
'operador': [
    'view_dashboard',        # Ver dashboard
    'registrar_entrada',     # Registrar entrada
    'registrar_saida',       # Registrar saída
    'view_estoque',          # Visualizar estoque
    'criar_chamado'          # Criar chamado
]
```

### Usuário - Apenas Leitura
```python
'usuario': [
    'view_estoque',          # Visualizar estoque
    'criar_chamado'          # Criar chamado
]
```

---

## Uso em Templates

### Verificar Permissão

```html
{% if can_perform('delete_product') %}
    <button class="btn btn-danger">Deletar Produto</button>
{% endif %}
```

### Verificar Role

```html
{% if current_user.role == 'admin' %}
    <a href="/admin/users">Gerenciar Usuários</a>
{% endif %}
```

### Mostrar Menu Condicional

```html
<ul class="navbar">
    <li><a href="/estoque">Estoque</a></li>
    
    {% if can_perform('view_reports') %}
        <li><a href="/relatorios">Relatórios</a></li>
    {% endif %}
    
    {% if can_perform('manage_users') %}
        <li><a href="/admin/users">Usuários</a></li>
    {% endif %}
    
    {% if current_user.is_admin %}
        <li><a href="/admin/audit-log">Auditoria</a></li>
    {% endif %}
</ul>
```

---

## Gerenciamento de Usuários (Admin)

### Criar Novo Usuário

```
POST /admin/users/create
Campos:
- username: string (3-80 caracteres)
- password: string (validação de força)
- role: string (admin, gerente, operador, usuario)
- area: string (opcional)
- localizacao: string (opcional)
```

### Editar Usuário

```
POST /admin/users/<id>/edit
Campos:
- role: string
- area: string
- localizacao: string
- ativo: boolean (bloqueado/desbloqueado)
```

### Deletar Usuário

```
POST /admin/users/<id>/delete
Proteção: Não permite deletar a si mesmo ou o último admin
```

### Resetar Senha

```
POST /admin/users/<id>/reset-password
Parâmetros:
- nova_senha: string (com validação)
```

### Bloquear/Desbloquear Account

```
POST /admin/users/<id>/toggle-block
Resultado: Ativa/desativa a conta
```

---

## Eventos de Auditoria

Todos os eventos de segurança são registrados:

| Tipo de Evento | Descrição |
|----------------|-----------|
| `login_sucesso` | Login bem-sucedido |
| `login_falho` | Tentativa de login falha |
| `login_falho_bloqueado` | Tentativa com conta bloqueada |
| `senha_alterada` | Usuário alterou sua senha |
| `password_reset` | Admin resetou senha |
| `usuario_criado` | Novo usuário criado |
| `usuario_editado` | Usuário foi editado |
| `usuario_deletado` | Usuário foi deletado |
| `usuario_bloqueado` | Conta foi bloqueada |
| `usuario_desbloqueado` | Conta foi desbloqueada |
| `tentativa_mudanca_senha_falha` | Tentativa falha de mudança de senha |
| `senha_esquecida` | Usuário solicita redefinição |

### Ver Logs

```
GET /admin/audit-log
```

Filtros disponíveis:
- `tipo`: Tipo de evento
- `usuario`: Usuário responsável
- `page`: Número da página

---

## Campos de Segurança do Usuário

### No Banco de Dados

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255),                    -- Hash PBKDF2-SHA256
    role VARCHAR(50),                         -- admin, gerente, operador, usuario
    area VARCHAR(255),
    localizacao VARCHAR(255),
    ativo BOOLEAN DEFAULT TRUE,              -- Ativo/Bloqueado
    ultimo_login DATETIME,                   -- Último login bem-sucedido
    tentativas_login_falhas INTEGER,         -- Contador de tentativas
    bloqueado_ate DATETIME,                  -- Bloqueio temporário
    data_criacao DATETIME,
    data_atualizacao DATETIME
);
```

### Propriedades do Objeto User

```python
user = User.query.first()

# Segurança
user.ativo                        # Boolean - se está ativo
user.tentativas_login_falhas      # Integer - tentativas falhas
user.bloqueado_ate               # DateTime - até quando está bloqueado
user.ultimo_login                # DateTime - último login bem-sucedido

# Métodos úteis
user.pode_tentar_login()              # Boolean, verifica se pode fazer login
user.registrar_login_sucesso()        # Reseta tentativas, registra login
user.registrar_login_falho(max=5)     # Incrementa tentativas, bloqueia se >= max
user.minutos_ate_desbloqueio()        # Integer, minutos até poder fazer login novamente
user.to_dict()                        # Converte para dicionário (sem password)
```

---

## Exemplo: Criar Usuário Admin Pro

```python
from app.auth.security import PasswordValidator

# Validar senha
is_valid, errors = PasswordValidator.validate("Meu@Password123")
if not is_valid:
    print("Senha inválida:", errors)
    exit()

# Hash da senha
password_hash = PasswordValidator.hash_password("Meu@Password123")

# Criar usuário
novo_admin = User(
    username="admin2",
    password=password_hash,  # Já em hash!
    role="admin",
    area="TI",
    localizacao="Sala 10"
)

from app.database import db
db.session.add(novo_admin)
db.session.commit()

print(f"Admin criado: {novo_admin.username}")
```

---

## Proteção contra Vulnerabilidades

### ✅ Proteção Implementada

1. **Proteção contra Força Bruta**
   - Bloqueio temporário após 5 tentativas
   - Contador de tentativas resetado após login bem-sucedido

2. **Senhas Seguras**
   - Hash com PBKDF2-SHA256
   - Validação de complexidade (maiúscula, minúscula, número)
   - Score de força da senha

3. **Open Redirect Prevention**
   - Validação de URLs de redirecionamento seguras
   - Só permite redirecionamentos relativos

4. **Session Security**
   - Flask-Login gerencia sessões corretamente
   - Logout limpa sessão completamente

5. **RBAC Granular**
   - Controle fino sobre permissões
   - Decoradores para proteção de rotas

6. **Auditoria Completa**
   - Todos os eventos de segurança registrados
   - Rastreamento de quem fez o quê e quando

---

## Boas Práticas

### ✅ DO's

```python
# Validar SEMPRE
@app.route('/admin/delete')
@require_permission('delete_user')
def deletar():
    # Já está protegido
    pass

# Usar decoradores
@require_role('admin')
@login_required
def funcao_protegida():
    pass

# Hashar senhas
password_hash = PasswordValidator.hash_password(password)

# Verificar em templates
{% if can_perform('delete') %}
    <button>Deletar</button>
{% endif %}
```

### ❌ DON'Ts

```python
# Não guardar senhas em plain text
user.password = "123456"  # ❌ NUNCA FAÇA ISSO

# Não confiar em input do usuário
if request.form['role'] == 'admin':  # ❌ Usuário pode forjar isso
    ...

# Não verificar a si mesmo em rotas críticas
@app.route('/admin/delete-self/<id>')
def deletar():
    db.session.delete(User.query.get(id))  # ❌ Sem verificação
```

---

## Troubleshooting

### "Acesso Negado (403)"
- Verifique seu role: `current_user.role`
- Verifique permissões: `get_user_permissions()`
- Contacte um administrador

### "Minha conta foi bloqueada"
- Você fez mais de 5 tentativas de login
- Aguarde 15 minutos para desbloquear
- Contacte admin para help

### "Senha fraca"
- Adicione uma MAIÚSCULA (A-Z)
- Adicione um número (0-9)
- Use mínimo 6 caracteres

### "Não consigo deletar usuário"
- Verificar se é o último admin (não pode deletar)
- Não é permitido deletar a si mesmo
- Apenas users com `delete_user` permission

---

## Próximos Passos de Segurança

- 🔐 2FA (Two-Factor Authentication)
- 🔑 OAuth2 / LDAP
- 📧 Verificação de email
- 🚨 Alertas de login suspeito
- 🔄 Renovação de senha periódica
- 📱 Autenticação por SMS

---

**Última atualização:** 2024
**Versão:** RBAC 1.0

# 🔐 RBAC Quick Reference

## Login & Logout

```python
from flask_login import login_user, logout_user, current_user

# Check if logged in
if current_user.is_authenticated:
    print(f"Logged in as: {current_user.username}")
    print(f"Role: {current_user.role}")  # admin, gerente, operador, usuario
    print(f"Is admin: {current_user.is_admin}")

# Logout
logout_user()
```

## Protect Routes

```python
from app.auth import require_role, require_permission, require_authenticated

# Only admin
@app.route('/admin')
@require_role('admin')
def admin_panel():
    pass

# Admin or gerente
@app.route('/produtos/novo')
@require_role('admin', 'gerente')
def novo_produto():
    pass

# Specific permission
@app.route('/usuarios/deletar/<id>', methods=['POST'])
@require_permission('delete_user')
def deletar_usuario(id):
    pass

# Just authenticated
@app.route('/perfil')
@require_authenticated()
def meu_perfil():
    pass
```

## Permissions

```python
from app.auth import can_perform, get_user_permissions, ROLES_PERMISSIONS

# Check permission in code
if can_perform('delete_user'):
    # Delete the user
    pass

# Get all permissions of current user
perms = get_user_permissions()
print(perms)  # ['view_dashboard', 'create_produto', ...]

# Get all permissions of a role
admin_perms = ROLES_PERMISSIONS['admin']
gerente_perms = ROLES_PERMISSIONS['gerente']
```

## In Templates

```html
<!-- Check permission -->
{% if can_perform('delete_product') %}
    <button class="btn btn-danger">Delete</button>
{% endif %}

<!-- Check role -->
{% if current_user.role == 'admin' %}
    <a href="/admin">Admin Panel</a>
{% endif %}

<!-- High level check -->
{% if current_user.is_admin %}
    Admin tools visible
{% endif %}

<!-- List of permissions -->
{% for perm in get_user_permissions() %}
    <li>{{ perm }}</li>
{% endfor %}
```

## Password Validation

```python
from app.auth.security import PasswordValidator

# Validate password strength
is_valid, errors = PasswordValidator.validate("MyPassword123")
if not is_valid:
    print("Password errors:", errors)
    # Errors like: ["Senha deve conter maiúscula", ...]

# Get strength score (0-100)
score = PasswordValidator.strength_score("Admin@123456")
print(f"Strength: {score}%")

# Hash password
pwd_hash = PasswordValidator.hash_password("MyPassword@123")
user.password = pwd_hash
db.session.commit()

# Verify password
correct = PasswordValidator.verify_password("MyPassword@123", pwd_hash)
```

## User Management

```python
from app.models import User
from app.auth.security import PasswordValidator

# Create user
new_user = User(
    username="john",
    password=PasswordValidator.hash_password("SecurePass@123"),
    role="operador",
    area="Warehouse",
    localizacao="Building 1"
)
db.session.add(new_user)
db.session.commit()

# Check if user can login
user = User.query.filter_by(username="john").first()
if user.pode_tentar_login():
    print("Can attempt login")
else:
    minutos = user.minutos_ate_desbloqueio()
    print(f"Blocked for {minutos} more minutes")

# Register successful login
user.registrar_login_sucesso()  # Reset attempts

# Register failed login
user.registrar_login_falho()  # Increment, may block

# Deactivate user
user.ativo = False
db.session.commit()

# Reset password (admin)
user.password = PasswordValidator.hash_password("NewPass@123")
user.tentativas_login_falhas = 0
user.bloqueado_ate = None
db.session.commit()
```

## Check User State

```python
from app.models import User

user = User.query.filter_by(username="john").first()

# State
print(user.ativo)                    # True/False
print(user.role)                     # admin/gerente/operador/usuario
print(user.ultimo_login)             # datetime or None
print(user.tentativas_login_falhas)  # int
print(user.bloqueado_ate)            # datetime or None

# Checks
print(user.is_admin)                 # bool
print(user.pode_tentar_login())      # bool
print(user.minutos_ate_desbloqueio()) # int
```

## Audit Events

```python
# Events are logged automatically, but you can also do

from app.utils import registrar_evento

registrar_evento(
    tipo_evento='acoes_critica',
    descricao='Descrição da ação',
    usuario_responsavel=current_user.username
)

# View events
from app.models import Historico

eventos = Historico.query.order_by(Historico.data_evento.desc()).limit(20).all()
for evento in eventos:
    print(f"{evento.data_evento} - {evento.tipo_evento}: {evento.descricao}")
```

## Roles & Permissions Matrix

| Route/Action | admin | gerente | operador | usuario |
|-------------|-------|---------|----------|---------|
| /admin/users | ✅ | ❌ | ❌ | ❌ |
| /admin/audit-log | ✅ | ❌ | ❌ | ❌ |
| /produtos/novo | ✅ | ✅ | ❌ | ❌ |
| /movimentacoes/entrada | ✅ | ❌ | ✅ | ❌ |
| /estoque | ✅ | ✅ | ✅ | ✅ |
| /chamada/nova | ✅ | ✅ | ✅ | ✅ |

## Common Tasks

### Create Admin User
```python
from app import create_app
from app.auth.security import PasswordValidator
from app.models import User
from app.database import db

app = create_app()
with app.app_context():
    user = User(
        username="admin2",
        password=PasswordValidator.hash_password("Admin@Pass2024"),
        role="admin"
    )
    db.session.add(user)
    db.session.commit()
    print("Admin created!")
```

### Reset Admin Password
```python
user = User.query.filter_by(username="admin").first()
user.password = PasswordValidator.hash_password("NewAdmin@123")
user.tentativas_login_falhas = 0
user.bloqueado_ate = None
db.session.commit()
print("Password reset!")
```

### Block User
```python
user = User.query.filter_by(username="john").first()
user.ativo = False
db.session.commit()
print(f"User {user.username} blocked!")
```

### Unblock User
```python
user = User.query.filter_by(username="john").first()
user.ativo = True
user.tentativas_login_falhas = 0
user.bloqueado_ate = None
db.session.commit()
print(f"User {user.username} unblocked!")
```

### List All Users
```python
users = User.query.all()
for user in users:
    print(f"{user.username:15} {user.role:10} ativo={user.ativo} últ_login={user.ultimo_login}")
```

## Error Codes

| Error | Meaning | Solution |
|-------|---------|----------|
| 403 Forbidden | Role/Permission denied | Check your role or ask admin |
| "Account locked" | Too many failed attempts | Wait 15 minutes or contact admin |
| "Weak password" | Password doesn't meet requirements | Add uppercase, lowercase and numbers |
| "Username taken" | Username already exists | Choose different username |

## Security Best Practices

```python
# DO:
✅ user.password = PasswordValidator.hash_password(pwd)
✅ @require_permission('delete_user')
✅ user.registrar_login_falho()
✅ registrar_evento(...)

# DON'T:
❌ user.password = "plain123"
❌ if request.form['role'] == 'admin':  # Check actual role!
❌ user.tentativas_login_falhas = 0  # Auto-managed
❌ Delete users without checking if last admin
```

---

Reference: [RBAC_GUIDE.md](./RBAC_GUIDE.md) - Full documentation

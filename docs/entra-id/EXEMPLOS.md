# Exemplos de integração — Entra ID

Snippets prontos para copiar e adaptar. Para o passo a passo de configuração, veja [SETUP.md](SETUP.md).

## 1. Link de login no template

```html
{% extends "base.html" %}
{% block content %}
<div class="login-container">
  <h1>Login - Sistema de Estoque</h1>

  <!-- Login tradicional (existente) -->
  <form method="POST" action="{{ url_for('auth.login') }}">
    {{ form.hidden_tag() }}
    <div>{{ form.username.label }} {{ form.username() }}</div>
    <div>{{ form.password.label }} {{ form.password() }}</div>
    <button type="submit">Entrar</button>
  </form>

  <hr><p>OU</p>

  <!-- Login via Entra ID -->
  <a href="{{ url_for('entra_auth.login') }}" class="btn btn-microsoft">
    Entrar com Microsoft Entra ID
  </a>
</div>
{% endblock %}
```

## 2. Decorator para exigir autenticação Entra ID

`app/auth/decorators.py`:

```python
from functools import wraps
from flask import redirect, url_for, flash
from app.routes.entra_auth import is_entra_authenticated

def require_entra_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_entra_authenticated():
            flash('Você precisa estar autenticado no Entra ID', 'warning')
            return redirect(url_for('entra_auth.login'))
        return f(*args, **kwargs)
    return decorated_function
```

## 3. Rota protegida usando o decorator

```python
from flask import Blueprint, render_template
from app.auth.decorators import require_entra_auth
from app.routes.entra_auth import get_entra_user_info

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@require_entra_auth
def dashboard():
    user_info = get_entra_user_info()
    return render_template('dashboard.html',
                           user_name=user_info['name'],
                           user_email=user_info['email'])
```

## 4. Sincronizar usuário Entra ID com o banco

Chame em `before_request`:

```python
from flask import g
from datetime import datetime
from app.models import User
from app.database import db
from app.routes.entra_auth import get_entra_user_info

def sync_entra_user_to_db():
    user_info = get_entra_user_info()
    if not user_info:
        return
    email = user_info.get('email')
    user = User.query.filter_by(email=email).first()
    if user:
        user.username = email.split('@')[0]
        user.ultimo_login = datetime.now()
        db.session.commit()
        g.user = user
    # Para criar automaticamente quando não existir, instancie um novo User
    # (password vazio, role='usuario') e faça db.session.add/commit.
```

## 5. Injetar helpers no contexto dos templates

Em `create_app()` (`app/__init__.py`):

```python
@app.context_processor
def inject_entra_auth():
    from app.routes.entra_auth import is_entra_authenticated, get_entra_user_info
    return {
        'is_entra_authenticated': is_entra_authenticated,
        'get_entra_user_info': get_entra_user_info,
    }
```

Uso no template:

```html
{% if is_entra_authenticated() %}
  <p>Olá {{ get_entra_user_info().name }}!</p>
  <a href="{{ url_for('entra_auth.logout') }}">Logout</a>
{% else %}
  <a href="{{ url_for('entra_auth.login') }}">Login com Entra ID</a>
{% endif %}
```

## 6. Validação de e-mail com regras extras

Variação de `validate_email_in_database()` com checagens adicionais (bloqueio, departamento):

```python
def validate_email_in_database(email: str) -> bool:
    from app.models import User
    if not email:
        return False
    try:
        email = email.strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user or not user.ativo:
            return False
        if user.bloqueado_ate and user.bloqueado_ate > datetime.now():
            return False
        if user.departamento not in ('TI', 'RH', 'Admin'):
            return False
        user.ultimo_login = datetime.now()
        user.tentativas_login_falhas = 0
        db.session.commit()
        return True
    except Exception as e:
        logging.error(f"Erro na validação: {e}")
        return False
```

## 7. Integração com Flask-Login

No `callback`, após validar o e-mail no BD:

```python
from flask_login import login_user
from app.models import User

user = User.query.filter_by(email=email).first()
if user:
    login_user(user, remember=False)
    session['is_entra_authenticated'] = True
    session['email'] = email
    session['name'] = user_info.get('name')
return redirect(url_for('main.index'))
```

## 8. Teste de integração

`tests/test_entra_auth.py`:

```python
from app import create_app

class TestEntraAuth:
    def setup_method(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_login_route_redirects(self):
        response = self.client.get('/entra/login')
        assert response.status_code == 302
        assert 'login.microsoftonline.com' in response.location

    def test_logout_clears_session(self):
        with self.client.session_transaction() as sess:
            sess['is_entra_authenticated'] = True
            sess['email'] = 'teste@empresa.com'
        self.client.get('/entra/logout')
        with self.client.session_transaction() as sess:
            assert 'is_entra_authenticated' not in sess
            assert 'email' not in sess
```

## 9. Proxy reverso com HTTPS (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name seu-dominio.com;

    ssl_certificate     /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name seu-dominio.com;
    return 301 https://$server_name$request_uri;
}
```

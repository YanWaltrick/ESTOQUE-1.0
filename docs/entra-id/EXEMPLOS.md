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

## 2. Exigir autenticação numa rota

Como o callback do Entra ID usa Flask-Login (`login_user`), basta o `@login_required`
padrão — não há necessidade de um decorator próprio de Entra ID:

```python
from flask_login import login_required, current_user

@app.route('/area-restrita')
@login_required
def area_restrita():
    return f"Olá, {current_user.username}"
```

## 3. Rota protegida com dados do usuário

```python
from flask import Blueprint, render_template
from flask_login import login_required, current_user

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html',
                           user_name=current_user.username,
                           user_email=current_user.email)
```

## 4. Sincronizar dados do usuário

O callback já preenche `entra_id` no primeiro login. Para sincronizar outros campos,
use `current_user` (Flask-Login) num `before_request` ou no próprio callback:

```python
from datetime import datetime
from flask_login import current_user
from app.database import db

def sync_entra_user():
    if not current_user.is_authenticated:
        return
    current_user.ultimo_login = datetime.now()
    db.session.commit()
```

## 5. Mostrar o usuário logado no template

O Flask-Login injeta `current_user` em todos os templates automaticamente — não é
preciso context processor:

```html
{% if current_user.is_authenticated %}
  <p>Olá {{ current_user.username }}!</p>
  <a href="{{ url_for('entra_auth.entra_logout') }}">Logout</a>
{% else %}
  <a href="{{ url_for('entra_auth.login') }}">Login com Entra ID</a>
{% endif %}
```

## 6. Regras de acesso extras no callback

O callback (`app/routes/entra_auth.py`) hoje só exige que o e-mail exista no BD. Para
restringir mais (conta ativa, não bloqueada, departamento), adicione as checagens
antes do `login_user`:

```python
# dentro de entra_auth_callback, após obter `user` por e-mail:
from datetime import datetime

if not user.ativo:
    flash("Conta inativa.", "error")
    return redirect(url_for('auth.login'))
if user.bloqueado_ate and user.bloqueado_ate > datetime.now():
    flash("Conta temporariamente bloqueada.", "error")
    return redirect(url_for('auth.login'))
if user.departamento not in ('TI', 'RH', 'Admin'):
    flash("Departamento sem acesso.", "error")
    return redirect(url_for('auth.login'))

login_user(user, remember=False)
```

## 7. Como o callback autentica (Flask-Login)

É exatamente o que `entra_auth_callback` faz: busca o usuário por e-mail e chama
`login_user` (sem chaves de sessão próprias — `current_user` basta):

```python
from flask_login import login_user
from app.models import User

user = User.query.filter_by(email=email).first()
if user:
    login_user(user, remember=False)
    return redirect(url_for('main.index'))
# Se o e-mail não existir, o callback abre uma Chamada para o admin (ver código).
```

## 8. Teste de integração (padrão pytest do projeto)

Use as fixtures de `tests/conftest.py`. Sem `ENTRA_*` configurado, `/entra/login`
redireciona para o login tradicional; o logout encerra a sessão Flask-Login:

```python
def test_entra_login_redireciona(client):
    resp = client.get('/entra/login')
    assert resp.status_code == 302  # vai ao Microsoft ou, sem config, ao /login

def test_entra_logout_encerra_sessao(auth_client):
    resp = auth_client.get('/entra/logout')
    assert resp.status_code == 302
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

"""
EXEMPLOS PRÁTICOS DE USO - Autenticação Entra ID

Este arquivo contém exemplos de como integrar a autenticação Entra ID
em diferentes partes da sua aplicação Flask.

Copie e adapte o código conforme necessário.
"""

# ============================================================================
# EXEMPLO 1: Adicionar Link de Login no Template HTML
# ============================================================================
# Arquivo: templates/login.html

HTML_LOGIN_TEMPLATE = """
{% extends "base.html" %}

{% block content %}
<div class="login-container">
    <h1>Login - Sistema de Estoque</h1>
    
    <!-- Login tradicional (existente) -->
    <form method="POST" action="{{ url_for('auth.login') }}">
        {{ form.hidden_tag() }}
        <div>
            {{ form.username.label }}
            {{ form.username() }}
        </div>
        <div>
            {{ form.password.label }}
            {{ form.password() }}
        </div>
        <button type="submit">Entrar</button>
    </form>
    
    <hr>
    <p>OU</p>
    
    <!-- Login via Entra ID (novo) -->
    <a href="{{ url_for('entra_auth.login') }}" class="btn btn-microsoft">
        🔐 Entrar com Microsoft Entra ID
    </a>
</div>

<style>
    .btn-microsoft {
        background-color: #0078d4;
        color: white;
        padding: 12px 24px;
        border-radius: 4px;
        text-decoration: none;
        display: inline-block;
        font-weight: bold;
    }
    .btn-microsoft:hover {
        background-color: #106ebe;
    }
</style>
{% endblock %}
"""


# ============================================================================
# EXEMPLO 2: Decorator para Exigir Autenticação Entra ID
# ============================================================================
# Arquivo: app/auth/decorators.py (adicionar função)

CODE_DECORATOR = """
from functools import wraps
from flask import session, redirect, url_for, flash
from app.routes.entra_auth import is_entra_authenticated

def require_entra_auth(f):
    '''
    Decorator que exige autenticação via Entra ID.
    
    Uso:
        @app.route('/dashboard')
        @require_entra_auth
        def dashboard():
            return render_template('dashboard.html')
    '''
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_entra_authenticated():
            flash('Você precisa estar autenticado no Entra ID', 'warning')
            return redirect(url_for('entra_auth.login'))
        return f(*args, **kwargs)
    return decorated_function
"""


# ============================================================================
# EXEMPLO 3: Rota Protegida usando o Decorator
# ============================================================================

CODE_PROTECTED_ROUTE = """
from flask import Blueprint, render_template
from app.auth.decorators import require_entra_auth
from app.routes.entra_auth import get_entra_user_info

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@require_entra_auth  # Exige autenticação Entra ID
def dashboard():
    user_info = get_entra_user_info()
    
    return render_template(
        'dashboard.html',
        user_name=user_info['name'],
        user_email=user_info['email']
    )
"""


# ============================================================================
# EXEMPLO 4: Middleware para Syncronizar Dados do Usuário
# ============================================================================

CODE_SYNC_USER = """
from flask import g, session
from app.models import User
from app.database import db

def sync_entra_user_to_db():
    '''
    Sincroniza dados do usuário Entra ID com o banco de dados.
    Chame em before_request da app.
    
    Isso pode:
    - Criar usuário no BD se não existir
    - Atualizar nome/departamento
    - Registrar último login
    '''
    from app.routes.entra_auth import get_entra_user_info
    
    user_info = get_entra_user_info()
    if not user_info:
        return
    
    email = user_info.get('email')
    name = user_info.get('name')
    
    # Buscar ou criar usuário
    user = User.query.filter_by(email=email).first()
    
    if user:
        # Atualizar dados
        user.username = email.split('@')[0]  # ou usar name
        # user.departamento = user_info.get('department', '')
        user.ultimo_login = datetime.now()
        db.session.commit()
        g.user = user
    
    # Se não existir e quiser criar automaticamente:
    # else:
    #     novo_user = User(
    #         username=email.split('@')[0],
    #         email=email,
    #         password='',  # Não tem senha (autenticado via Entra)
    #         role='usuario'
    #     )
    #     db.session.add(novo_user)
    #     db.session.commit()
"""


# ============================================================================
# EXEMPLO 5: Adicionar Função no Contexto de Templates
# ============================================================================

CODE_TEMPLATE_CONTEXT = """
# Em app/__init__.py, na função create_app():

@app.context_processor
def inject_entra_auth():
    '''Injetar funções de auth Entra ID nos templates'''
    from app.routes.entra_auth import is_entra_authenticated, get_entra_user_info
    return {
        'is_entra_authenticated': is_entra_authenticated,
        'get_entra_user_info': get_entra_user_info,
    }

# Uso em templates:
# {% if is_entra_authenticated() %}
#     <p>Olá {{ get_entra_user_info().name }}!</p>
#     <a href="{{ url_for('entra_auth.logout') }}">Logout</a>
# {% else %}
#     <a href="{{ url_for('entra_auth.login') }}">Login com Entra ID</a>
# {% endif %}
"""


# ============================================================================
# EXEMPLO 6: Validação Customizada de Email
# ============================================================================

CODE_CUSTOM_VALIDATION = """
# Arquivo: app/auth/entra_id.py - Função customize

def validate_email_in_database(email: str) -> bool:
    '''
    Exemplo de validação com múltiplas condições.
    '''
    from app.models import User
    
    if not email:
        return False
    
    try:
        email = email.strip().lower()
        
        # Buscar usuário
        user = User.query.filter_by(email=email).first()
        
        if not user:
            logging.info(f"Email não encontrado: {email}")
            return False
        
        # Verificar se está ativo
        if not user.ativo:
            logging.warning(f"Usuário inativo: {email}")
            return False
        
        # OPCIONAL: Adicionar mais validações
        
        # Verificar se está bloqueado por tentativas falhas
        if user.bloqueado_ate and user.bloqueado_ate > datetime.now():
            logging.warning(f"Usuário bloqueado: {email}")
            return False
        
        # Verificar permissão por departamento (opcional)
        departamentos_permitidos = ['TI', 'RH', 'Admin']
        if user.departamento not in departamentos_permitidos:
            logging.warning(f"Departamento não autorizado: {user.departamento}")
            return False
        
        # Tudo OK
        user.ultimo_login = datetime.now()
        user.tentativas_login_falhas = 0  # Resetar contador
        db.session.commit()
        
        return True
    
    except Exception as e:
        logging.error(f"Erro na validação: {str(e)}")
        return False
"""


# ============================================================================
# EXEMPLO 7: Tratamento de Erro em Produção
# ============================================================================

CODE_ERROR_HANDLING = """
# Em app/__init__.py, adicione error handlers

@app.errorhandler(404)
def not_found(error):
    if is_entra_authenticated():
        return render_template('404.html', 
                             user_info=get_entra_user_info()), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    app_logger.error(f"Erro interno: {str(error)}")
    return render_template('500.html'), 500
"""


# ============================================================================
# EXEMPLO 8: Teste da Integração (Unit Test)
# ============================================================================

CODE_UNIT_TEST = """
# Arquivo: tests/test_entra_auth.py

from flask import session
from app import create_app

class TestEntraAuth:
    def setup_method(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def test_login_route_exists(self):
        '''Testar se rota de login existe'''
        response = self.client.get('/entra/login')
        # Deve redirecionar para Entra ID (302)
        assert response.status_code == 302
        assert 'login.microsoftonline.com' in response.location
    
    def test_validate_email_in_db(self):
        '''Testar validação de email'''
        from app.auth.entra_id import validate_email_in_database
        from app.models import User
        
        # Criar usuário de teste
        user = User(
            username='teste',
            password='hash',
            email='teste@empresa.com',
            ativo=True
        )
        # db.session.add(user)
        # db.session.commit()
        
        # Testar
        # assert validate_email_in_database('teste@empresa.com') == True
        # assert validate_email_in_database('naoexiste@empresa.com') == False
    
    def test_logout_clears_session(self):
        '''Testar se logout limpa sessão'''
        with self.client.session_transaction() as sess:
            sess['is_entra_authenticated'] = True
            sess['email'] = 'teste@empresa.com'
        
        response = self.client.get('/entra/logout')
        
        with self.client.session_transaction() as sess:
            assert 'is_entra_authenticated' not in sess
            assert 'email' not in sess
"""


# ============================================================================
# EXEMPLO 9: Integração com Flask-Login
# ============================================================================

CODE_FLASK_LOGIN_INTEGRATION = """
# Arquivo: app/routes/entra_auth.py - Modificar callback

from flask_login import login_user
from app.models import User

@entra_bp.route('/callback', methods=['GET'])
def callback():
    # ... código anterior ...
    
    # Após validar email no BD:
    email = user_info.get('email')
    user = User.query.filter_by(email=email).first()
    
    if user:
        # Fazer login automático via Flask-Login
        login_user(user, remember=False)
        
        # Salvar também na sessão para referência
        session['is_entra_authenticated'] = True
        session['email'] = email
        session['name'] = user_info.get('name')
    
    return redirect(url_for('main.index'))
"""


# ============================================================================
# EXEMPLO 10: Configurar em Produção (Nginx)
# ============================================================================

CODE_NGINX_CONFIG = """
# Arquivo: /etc/nginx/sites-available/estoque

server {
    listen 443 ssl http2;
    server_name seu-dominio.com;
    
    ssl_certificate /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Headers de segurança
        proxy_set_header X-Frame-Options "DENY";
        proxy_set_header X-Content-Type-Options "nosniff";
        proxy_set_header X-XSS-Protection "1; mode=block";
    }
}

server {
    listen 80;
    server_name seu-dominio.com;
    return 301 https://$server_name$request_uri;
}
"""


if __name__ == "__main__":
    print("Exemplos de uso da autenticação Entra ID")
    print("\nVer código-fonte deste arquivo para exemplos práticos")

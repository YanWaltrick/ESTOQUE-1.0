"""
Blueprint para autenticação via Microsoft Entra ID (Azure AD).

Implementa o fluxo OIDC com as seguintes rotas:
- /login/entra: Inicia o processo de autenticação
- /entra/login: Alias para iniciar o login
- /entra-callback: Recebe o código e realiza o login
- /entra-logout: Faz logout e limpa a sessão
"""

from flask import Blueprint, redirect, url_for, session, request, current_app, flash
from flask_login import login_user, logout_user
from datetime import datetime
from app.auth.entra_id import EntraIDConfig, EntraIDClient, create_csrf_token, create_or_update_user_from_entra_info

# Criar Blueprint
entra_bp = Blueprint('entra_auth', __name__)


@entra_bp.before_app_request
def init_entra_config():
    """Inicializa a configuração do Entra ID uma única vez por request."""
    if 'entra_config' not in session:
        try:
            config = EntraIDConfig()
            session['entra_config_ready'] = True
        except ValueError as e:
            current_app.logger.error(f"Erro ao inicializar Entra ID: {str(e)}")
            session['entra_config_ready'] = False


@entra_bp.route('/login/entra', methods=['GET'])
@entra_bp.route('/entra/login', methods=['GET'])
def login():
    """
    Rota de login que inicia o fluxo de autenticação OIDC.
    
    1. Gera um token CSRF para proteger contra ataques
    2. Cria a URL de autenticação do Entra ID
    3. Redireciona o usuário para o Entra ID
    """
    try:
        config = EntraIDConfig()
        client = EntraIDClient(config)

        csrf_token = create_csrf_token()
        session['entra_csrf_token'] = csrf_token

        base_url = request.host_url.rstrip('/')
        auth_url = client.get_auth_url(base_url, state=csrf_token)

        current_app.logger.info("Usuário redirecionado para autenticação Entra ID")
        return redirect(auth_url)

    except Exception as e:
        current_app.logger.error(f"Erro na rota /entra/login: {str(e)}")
        flash('Erro ao iniciar autenticação Entra ID. Verifique sua configuração.', 'error')
        return redirect(url_for('auth.login'))


@entra_bp.route('/entra-callback', methods=['GET'])
def callback():
    """
    Rota de callback que processa a resposta do Entra ID.
    
    Fluxo:
    1. Valida o token CSRF (state)
    2. Captura o código de autorização
    3. Troca o código por tokens de acesso
    4. Busca dados do usuário (name, email)
    5. Valida se o email existe no banco de dados
    6. Salva os dados na sessão Flask
    7. Redireciona para a página principal
    """
    try:
        # ====== ETAPA 1: Validar CSRF Token ======
        state = request.args.get('state')
        csrf_token = session.pop('entra_csrf_token', None)
        
        if not state or state != csrf_token:
            current_app.logger.warning("Validação CSRF falhou no callback Entra ID")
            flash('Erro: Token CSRF inválido', 'error')
            return redirect(url_for('main.index'))
        
        # ====== ETAPA 2: Validar presença do código ======
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            error_description = request.args.get('error_description', 'Desconhecido')
            current_app.logger.error(f"Erro do Entra ID: {error} - {error_description}")
            flash(f'Erro de autenticação: {error_description}', 'error')
            return redirect(url_for('main.index'))
        
        if not code:
            current_app.logger.warning("Código de autorização não recebido")
            flash('Erro: Código de autorização não recebido', 'error')
            return redirect(url_for('main.index'))
        
        # ====== ETAPA 3: Trocar código por tokens ======
        config = EntraIDConfig()
        client = EntraIDClient(config)
        
        base_url = request.host_url.rstrip('/')
        token_response = client.acquire_token_by_code(code, base_url)
        
        if not token_response:
            current_app.logger.error("Falha ao adquirir token via código")
            flash('Erro ao processar autenticação', 'error')
            return redirect(url_for('main.index'))
        
        # ====== ETAPA 4: Buscar dados do usuário ======
        user_info = client.get_user_info(token_response)
        
        if not user_info:
            current_app.logger.error("Falha ao buscar dados do usuário")
            flash('Erro ao obter dados do usuário', 'error')
            return redirect(url_for('main.index'))
        
        email = user_info.get('email')
        name = user_info.get('name')
        upn = user_info.get('upn')
        
        # ====== ETAPA 5: Criar ou atualizar usuário local ======
        user = create_or_update_user_from_entra_info(user_info)
        if not user:
            current_app.logger.warning(f"Usuário não autorizado ou inativo: {email}")
            flash(f'Usuário {email} não está autorizado no sistema', 'error')
            return redirect(url_for('auth.login'))

        # ====== ETAPA 6: Login local via Flask-Login ======
        login_user(user, remember=False)
        user.registrar_login_sucesso()
        session['last_activity'] = datetime.utcnow().isoformat()
        session['entra_id'] = user_info.get('id')
        session['name'] = name
        session['email'] = email
        session['upn'] = upn
        session['is_entra_authenticated'] = True
        current_app.logger.info(f"Usuário {email} autenticado via Entra ID e logado localmente")
        flash(f'Bem-vindo, {name}!', 'success')

        return redirect(url_for('main.index'))
    
    except Exception as e:
        current_app.logger.error(f"Exceção na rota /entra-callback: {str(e)}")
        flash('Erro ao processar callback de autenticação', 'error')
        return redirect(url_for('main.index'))


@entra_bp.route('/entra-logout', methods=['GET'])
def logout():
    """
    Rota de logout que limpa a sessão local e redireciona para logout do Entra ID.
    
    Fluxo:
    1. Captura os dados atuais da sessão
    2. Limpa a sessão Flask
    3. Gera a URL de logout do Entra ID
    4. Redireciona para logout no Entra ID
    """
    try:
        # Obter informações do usuário antes de limpar a sessão
        email = session.get('email', 'Desconhecido')
        
        # ====== LIMPAR SESSÃO LOCAL ======
        # Remover dados da sessão
        session.pop('entra_id', None)
        session.pop('name', None)
        session.pop('email', None)
        session.pop('upn', None)
        session.pop('is_entra_authenticated', None)
        
        # Se você estiver usando Flask-Login, também fazer logout
        from flask_login import logout_user
        logout_user()
        
        current_app.logger.info(f"Usuário {email} desconectado do Entra ID")
        
        # ====== REDIRECIONAR PARA LOGOUT DO ENTRA ID ======
        config = EntraIDConfig()
        client = EntraIDClient(config)
        
        # URL para redirecionar após logout no Entra ID
        post_logout_redirect = request.host_url.rstrip('/') + url_for('main.index')
        
        logout_url = client.get_logout_url(post_logout_redirect)
        
        flash('Você foi desconectado', 'info')
        return redirect(logout_url)
    
    except Exception as e:
        current_app.logger.error(f"Erro na rota /entra-logout: {str(e)}")
        flash('Erro ao desconectar', 'error')
        return redirect(url_for('main.index'))


def is_entra_authenticated():
    """
    Função auxiliar para verificar se o usuário está autenticado via Entra ID.
    
    Returns:
        True se autenticado, False caso contrário
    """
    return session.get('is_entra_authenticated', False)


def get_entra_user_info():
    """
    Função auxiliar para obter informações do usuário autenticado via Entra ID.
    
    Returns:
        Dicionário com id, name, email e upn, ou None se não autenticado
    """
    if not is_entra_authenticated():
        return None
    
    return {
        'id': session.get('entra_id'),
        'name': session.get('name'),
        'email': session.get('email'),
        'upn': session.get('upn'),
    }

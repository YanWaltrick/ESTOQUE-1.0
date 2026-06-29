"""
Rotas de autenticação Microsoft Entra ID
Gerencia login, callback e logout via Microsoft
"""

import logging
from flask import Blueprint, request, redirect, url_for, session, flash, current_app
from flask_login import login_user, logout_user, current_user

from app.models import User, Chamada
from app.database import db
from app.auth.entra_id import create_entra_client
from app.services.notification_service import enviar_notificacao_chamada

logger = logging.getLogger(__name__)

entra_bp = Blueprint('entra_auth', __name__, url_prefix='/entra')


def _get_redirect_uri():
    """Constrói redirect_uri completo (scheme + host + path)"""
    scheme = 'https' if current_app.config.get('SESSION_COOKIE_SECURE') else 'http'
    host = request.host
    redirect_path = current_app.config.get('ENTRA_REDIRECT_PATH', '/entra-callback')
    return f"{scheme}://{host}{redirect_path}"


@entra_bp.route('/login', methods=['GET'])
def login():
    """
    Inicia fluxo de autenticação Microsoft
    Redireciona para Microsoft login
    """
    try:
        entra_client = create_entra_client(session)
        
        if not entra_client:
            logger.error("Cliente Entra ID não está configurado")
            flash("Autenticação Microsoft não está disponível no momento", "error")
            return redirect(url_for('auth.login'))
        
        # Gerar URL de autenticação
        redirect_uri = _get_redirect_uri()
        auth_url, state = entra_client.get_auth_url(redirect_uri)
        
        # State já foi armazenado em entra_client.session_store
        # Agora guardar em session do Flask
        session['auth_state'] = state
        
        logger.info(f"Redirecionando para Microsoft login")
        return redirect(auth_url)
    
    except Exception as e:
        logger.error(f"Erro ao iniciar login Entra ID: {str(e)}")
        flash("Erro ao iniciar autenticação", "error")
        return redirect(url_for('auth.login'))


@entra_bp.route('/callback', methods=['GET'])
def entra_auth_callback():
    """
    Callback do Microsoft após autenticação
    Valida token e faz login ou cria chamado de solicitação
    """
    try:
        # Capturar código e state da query string
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        error_description = request.args.get('error_description')
        
        # Verificar erros do Microsoft
        if error:
            logger.warning(f"Erro do Microsoft: {error} - {error_description}")
            flash(f"Erro de autenticação: {error_description or error}", "error")
            return redirect(url_for('auth.login'))
        
        if not code:
            logger.error("Código de autorização não recebido")
            flash("Erro na autenticação - código não recebido", "error")
            return redirect(url_for('auth.login'))
        
        # Inicializar cliente Entra ID
        entra_client = create_entra_client(session)
        if not entra_client:
            logger.error("Cliente Entra ID não está configurado")
            flash("Autenticação Microsoft não está disponível", "error")
            return redirect(url_for('auth.login'))
        
        # Validar token com CSRF protection
        redirect_uri = _get_redirect_uri()
        session_state = session.get('auth_state')
        
        token_result = entra_client.validate_token(code, redirect_uri, session_state)
        
        if not token_result:
            logger.error("Falha ao validar token")
            flash("Erro ao validar autenticação", "error")
            return redirect(url_for('auth.login'))
        
        # Extrair informações do usuário
        user_info = entra_client.extract_user_info(token_result)
        
        if not user_info:
            logger.error("Falha ao extrair informações do usuário")
            flash("Erro ao obter informações do usuário", "error")
            return redirect(url_for('auth.login'))
        
        email = user_info.get('email', '').lower().strip()
        oid = user_info.get('oid')
        
        if not email or not oid:
            logger.error(f"Email ou OID inválido: email={email}, oid={oid}")
            flash("Informações incompletas do Microsoft", "error")
            return redirect(url_for('auth.login'))
        
        logger.info(f"Usuário autenticado no Microsoft: email={email}, oid={oid}")
        
        # ========== LÓGICA PRINCIPAL ==========
        # Buscar usuário no BD pelo email
        user = User.query.filter_by(email=email).first()
        
        if user:
            # ✅ Usuário existe - fazer login
            logger.info(f"Usuário encontrado no sistema: {user.username}")
            
            # Atualizar entra_id se não estiver preenchido (para audit trail)
            if not user.entra_id:
                user.entra_id = oid
                db.session.commit()
                logger.info(f"Campo entra_id preenchido para user {user.username}")
            
            # Fazer login
            login_user(user, remember=False)
            logger.info(f"Login bem-sucedido para {user.username} via Entra ID")
            
            # Limpar state da sessão
            session.pop('auth_state', None)
            
            flash(f"Bem-vindo, {user.email}!", "success")
            return redirect(url_for('main.index'))
        
        else:
            # ❌ Usuário NÃO existe - criar chamado de solicitação
            logger.warning(f"Novo email tentou acessar sistema: {email} (OID: {oid})")
            
            # Criar chamada automática para admin
            mensagem = (
                f"[Acesso Sistema - Solicitação Entra ID]\n\n"
                f"Novo usuário solicitou acesso via Microsoft.\n\n"
                f"Email: {email}\n"
                f"OID (Microsoft): {oid}\n\n"
                f"Ação: Criar usuário no sistema se aprovado."
            )
            
            # Criar chamada (user_id=1 é o admin por default, mas isso será atualizado)
            # Na verdade, vamos criar sem usuário específico ou com um sistema user
            try:
                # Buscar um admin para associar a chamada
                admin_user = User.query.filter_by(role='admin').first()
                admin_id = admin_user.id if admin_user else 1  # Fallback para ID 1
                
                chamada = Chamada(
                    id_usuario=admin_id,  # Associar ao admin (ou usar ID genérico)
                    mensagem=mensagem,
                    foto_anexo=None,
                    status='nova'
                )
                
                db.session.add(chamada)
                db.session.commit()
                
                logger.info(f"Chamada criada para acesso de {email} (ID: {chamada.id_chamada})")
                
                # Tentar enviar notificação ao Teams
                try:
                    enviar_notificacao_chamada(chamada, 'chamada_criada')
                    logger.info("Notificação Teams enviada para nova solicitação de acesso")
                except Exception as e:
                    logger.warning(f"Não foi possível enviar notificação Teams: {str(e)}")
            
            except Exception as e:
                logger.error(f"Erro ao criar chamada de solicitação: {str(e)}")
                flash("Erro ao processar solicitação", "error")
                return redirect(url_for('auth.login'))
            
            # Limpar state da sessão
            session.pop('auth_state', None)
            
            flash(
                "Seu email não existe no sistema. Uma solicitação foi enviada ao "
                "administrador. Aguarde a aprovação.",
                "info"
            )
            return redirect(url_for('auth.login'))
    
    except Exception as e:
        logger.error(f"Erro no callback Entra ID: {str(e)}", exc_info=True)
        flash("Erro na autenticação", "error")
        return redirect(url_for('auth.login'))


@entra_bp.route('/logout', methods=['GET'])
def entra_logout():
    """
    Logout do sistema
    Limpa sessão Flask e redireciona para logout do Microsoft
    """
    try:
        user_email = current_user.email if current_user.is_authenticated else "unknown"
        
        # Logout do Flask
        logout_user()
        
        # Limpar sessão
        session.clear()
        
        logger.info(f"Logout Entra ID: {user_email}")
        
        flash("Você foi desconectado", "info")
        
        # Redirecionar para Microsoft logout (opcional, mas bom para segurança)
        # GET https://login.microsoftonline.com/{tenant}/oauth2/v2.0/logout?post_logout_redirect_uri={uri}
        tenant_id = current_app.config.get('ENTRA_TENANT_ID')
        if tenant_id:
            redirect_after_logout = url_for('auth.login', _external=True)
            microsoft_logout_url = (
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout"
                f"?post_logout_redirect_uri={redirect_after_logout}"
            )
            return redirect(microsoft_logout_url)
        
        return redirect(url_for('auth.login'))
    
    except Exception as e:
        logger.error(f"Erro no logout Entra ID: {str(e)}")
        session.clear()
        return redirect(url_for('auth.login'))

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timezone, timedelta
from app.database import db
from app.models import User, Chamada
from app.utils import registrar_evento
from app.auth.security import PasswordValidator, validate_username

auth_bp = Blueprint('auth', __name__)


def agora_gmt3():
    """Retorna datetime com fuso-horário GMT-3."""
    return datetime.now(timezone(timedelta(hours=-3)))


def url_has_allowed_host_and_scheme(url, allowed_hosts=None):
    """
    Verifica se a URL é segura para redirecionamento.
    Previne open redirect vulnerabilities.
    """
    if allowed_hosts is None:
        allowed_hosts = ['localhost', '127.0.0.1']
    
    if not url:
        return False
    
    # Não permitir URLs que começam com // (protocol-relative)
    if url.startswith('//'):
        return False
    
    from urllib.parse import urlparse
    parsed = urlparse(url)
    
    # URL relativa é segura
    if not parsed.netloc:
        return True
    
    # Verificar se o host está na lista de máquinas permitidas
    return parsed.netloc in allowed_hosts

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login com proteção contra força bruta"""
    if current_user.is_authenticated:
        return redirect(url_for('main.admin') if current_user.is_admin else url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # Validação básica
        if not username or not password:
            flash('Nome de usuário e senha são obrigatórios.', 'error')
            return render_template('login.html')

        # Buscar usuário
        user = User.query.filter_by(username=username).first()

        # Usuário não existe
        if not user:
            flash('Nome de usuário ou senha incorretos.', 'error')
            registrar_evento(
                tipo_evento='login_falho',
                descricao=f'Tentativa de login com usuário inexistente: "{username}"',
                usuario_responsavel='Sistema'
            )
            return render_template('login.html')

        # Verificar se está ativo
        if not user.ativo:
            flash('Sua conta foi desativada. Contate um administrador.', 'error')
            registrar_evento(
                tipo_evento='login_falho_bloqueado',
                descricao=f'Tentativa de login com conta desativada: "{username}"',
                usuario_responsavel='Sistema'
            )
            return render_template('login.html')

        # Verificar bloqueio por força bruta
        if not user.pode_tentar_login():
            minutos = user.minutos_ate_desbloqueio()
            flash(f'Sua conta foi bloqueada temporariamente por múltiplas tentativas falhas. Tente novamente em {minutos} minuto(s).', 'error')
            return render_template('login.html')

        # Verificar senha
        if not PasswordValidator.verify_password(password, user.password):
            user.registrar_login_falho()
            flash('Nome de usuário ou senha incorretos.', 'error')
            registrar_evento(
                tipo_evento='login_falho',
                descricao=f'Tentativa de login falha: "{username}" (tentativa #{user.tentativas_login_falhas})',
                usuario_responsavel='Sistema'
            )
            return render_template('login.html')

        # Login bem-sucedido
        user.registrar_login_sucesso()
        login_user(user, remember=request.form.get('remember') == 'on')
        
        registrar_evento(
            tipo_evento='login_sucesso',
            descricao=f'Login bem-sucedido: "{user.username}" (role: {user.role})',
            usuario_responsavel=user.username
        )

        # Redirecionar para página apropriada
        next_page = request.args.get('next')
        if next_page and url_has_allowed_host_and_scheme(next_page):
            return redirect(next_page)
        
        if user.role == 'admin':
            return redirect(url_for('main.admin', tab='chamadas'))
        else:
            return redirect(url_for('main.index'))

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    session.pop('perfil_verified', None)
    session.pop('perfil_previous', None)
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    """Tela de perfil com reautenticação antes de permitir mudança de senha."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username != current_user.username or not check_password_hash(current_user.password, password):
            flash('Erro: login diferente ou senha inválida.', 'error')
            destino = session.pop('perfil_previous', None) or url_for('main.index')
            return redirect(destino)

        session['perfil_verified'] = True
        return redirect(url_for('auth.perfil'))

    if session.get('perfil_verified'):
        return render_template('profile.html', usuario=current_user.username)

    if 'perfil_previous' not in session:
        anterior = request.referrer
        if anterior and not anterior.endswith(url_for('auth.perfil')):
            session['perfil_previous'] = anterior
        else:
            session['perfil_previous'] = url_for('main.index')

    return render_template('profile_auth.html', usuario=current_user.username)

@auth_bp.route('/perfil/password', methods=['POST'])
@login_required
def perfil_password():
    if not session.get('perfil_verified'):
        flash('Por favor, reautentique para acessar o perfil.', 'error')
        return redirect(url_for('auth.perfil'))

    login_name = request.form.get('login_name', '').strip()
    senha_atual = request.form.get('senha_atual', '').strip()
    nova_senha = request.form.get('nova_senha', '').strip()
    confirm_nova_senha = request.form.get('confirm_nova_senha', '').strip()

    if login_name != current_user.username:
        flash('O nome de login informado deve ser o seu próprio login.', 'error')
        registrar_evento(
            tipo_evento='tentativa_mudanca_senha_falha',
            descricao=f'Tentativa de mudança de senha com username diferente',
            usuario_responsavel=current_user.username
        )
        return redirect(url_for('auth.perfil'))

    if not senha_atual or not nova_senha or not confirm_nova_senha:
        flash('Todos os campos são obrigatórios.', 'error')
        return redirect(url_for('auth.perfil'))

    if not PasswordValidator.verify_password(senha_atual, current_user.password):
        flash('Senha atual incorreta.', 'error')
        registrar_evento(
            tipo_evento='tentativa_mudanca_senha_falha',
            descricao=f'Tentativa com senha atual incorreta',
            usuario_responsavel=current_user.username
        )
        return redirect(url_for('auth.perfil'))

    if nova_senha != confirm_nova_senha:
        flash('A nova senha deve ser digitada duas vezes de forma idêntica.', 'error')
        return redirect(url_for('auth.perfil'))

    if senha_atual == nova_senha:
        flash('A nova senha deve ser diferente da senha atual.', 'error')
        return redirect(url_for('auth.perfil'))

    # Validar força da nova senha
    is_valid, errors = PasswordValidator.validate(nova_senha)
    if not is_valid:
        for error in errors:
            flash(f'Erro na nova senha: {error}', 'error')
        return redirect(url_for('auth.perfil'))

    # Atualizar senha
    current_user.password = PasswordValidator.hash_password(nova_senha)
    db.session.commit()

    registrar_evento(
        tipo_evento='senha_alterada',
        descricao=f'Senha alterada com sucesso',
        usuario_responsavel=current_user.username
    )

    flash('Senha atualizada com sucesso com segurança reforçada.', 'success')
    return redirect(url_for('auth.perfil'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        mensagem = request.form.get('mensagem', '').strip()

        if not username:
            flash('Informe o nome de usuário para solicitar a redefinição.', 'error')
            return redirect(url_for('auth.forgot_password'))

        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('auth.forgot_password'))

        texto = f'Esqueci a senha - usuário "{user.username}" solicita redefinição.'
        if mensagem:
            texto += f' Detalhes: {mensagem}'

        chamada = Chamada(id_usuario=user.id, mensagem=texto)
        db.session.add(chamada)
        db.session.commit()

        registrar_evento(
            tipo_evento='senha_esquecida',
            descricao=f'Chamado de redefinição de senha solicitado para "{user.username}"',
            usuario_responsavel='Sistema'
        )

        flash('Chamado de senha esquecida criado com sucesso. Um administrador irá analisar.', 'success')
        return redirect(url_for('auth.forgot_password'))

    return render_template('forgot_password.html')
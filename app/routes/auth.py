from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app, send_file
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timezone, timedelta
from flask_mail import Message
from werkzeug.security import check_password_hash
from app.database import db, mail
from app.models import User, Chamada
from app.utils import registrar_evento
from app.auth.security import PasswordValidator, validate_username, validate_email
import os

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
        # Carregar hosts permitidos da configuração
        env_hosts = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
        allowed_hosts = [host.strip() for host in env_hosts.split(',')]
    
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


def _smtp_configurado() -> bool:
    """Verifica se há configuração mínima para envio de e-mails."""
    return bool(current_app.config.get('MAIL_SERVER') and current_app.config.get('MAIL_DEFAULT_SENDER'))


def _emails_admin_destino() -> list[str]:
    """Monta lista de e-mails de administradores a notificar."""
    destinos = set()

    # Prioriza configuração explícita via variável de ambiente (se existir)
    admin_emails_env = (current_app.config.get('ADMIN_EMAILS') or '').strip()
    if admin_emails_env:
        for email in [item.strip() for item in admin_emails_env.split(',') if item.strip()]:
            is_valid, _ = validate_email(email)
            if is_valid:
                destinos.add(email)

    # Também usa usuários admin cujo username é um e-mail válido
    admins = User.query.filter_by(role='admin', ativo=True).all()
    for admin in admins:
        is_valid, _ = validate_email(admin.username)
        if is_valid:
            destinos.add(admin.username)

    return sorted(destinos)


def _enviar_emails_senha_esquecida(user: User, mensagem_texto: str) -> tuple[bool, str]:
    """Dispara notificações de senha esquecida para admins e usuário solicitante."""
    # Se SMTP não está configurado, apenas retorna sucesso (chamado foi salvo no BD)
    if not _smtp_configurado():
        return True, ''

    try:
        admins_destino = _emails_admin_destino()
        if admins_destino:
            assunto_admin = f'[SOMA ASSET] Solicitação de redefinição de senha - {user.username}'
            corpo_admin = (
                'Um usuário solicitou redefinição de senha.\n\n'
                f'Usuário: {user.username}\n'
                f'Mensagem: {mensagem_texto}\n'
                f'Data/Hora: {agora_gmt3().strftime("%d/%m/%Y %H:%M:%S")}\n'
            )
            msg_admin = Message(subject=assunto_admin, recipients=admins_destino, body=corpo_admin)
            mail.send(msg_admin)

        # Envia confirmação para o usuário somente se ele usa e-mail como login
        usuario_eh_email, _ = validate_email(user.username)
        if usuario_eh_email:
            assunto_usuario = '[SOMA ASSET] Recebemos sua solicitação de redefinição'
            corpo_usuario = (
                'Recebemos sua solicitação de redefinição de senha.\n\n'
                'Um administrador irá analisar e retornar em breve.\n'
                'Se você não fez esta solicitação, ignore este e-mail.\n'
            )
            msg_usuario = Message(subject=assunto_usuario, recipients=[user.username], body=corpo_usuario)
            mail.send(msg_usuario)

        return True, ''
    except Exception as e:
        current_app.logger.error('Falha ao enviar email de senha esquecida: %s', str(e))
        return False, str(e)

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
        # Registrar atividade da sessão para timeout de inatividade (aplica apenas para usuários)
        try:
            if user.role != 'admin':
                session.permanent = True
                session['last_activity'] = datetime.utcnow().isoformat()
        except Exception:
            pass
        
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
        return render_template('profile.html', usuario=current_user.username, foto_perfil=current_user.foto_perfil)

    if 'perfil_previous' not in session:
        anterior = request.referrer
        if anterior and not anterior.endswith(url_for('auth.perfil')):
            session['perfil_previous'] = anterior
        else:
            session['perfil_previous'] = url_for('main.index')

    return render_template('profile_auth.html', usuario=current_user.username)


@auth_bp.route('/perfil/senha', methods=['GET'])
@login_required
def perfil_senha():
    """Tela dedicada para redefinição de senha."""
    if not session.get('perfil_verified'):
        flash('Por favor, reautentique para acessar o perfil.', 'error')
        return redirect(url_for('auth.perfil'))

    return render_template('profile_password.html', usuario=current_user.username)

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
        return redirect(url_for('auth.perfil_senha'))

    if not senha_atual or not nova_senha or not confirm_nova_senha:
        flash('Todos os campos são obrigatórios.', 'error')
        return redirect(url_for('auth.perfil_senha'))

    if not PasswordValidator.verify_password(senha_atual, current_user.password):
        flash('Senha atual incorreta.', 'error')
        registrar_evento(
            tipo_evento='tentativa_mudanca_senha_falha',
            descricao=f'Tentativa com senha atual incorreta',
            usuario_responsavel=current_user.username
        )
        return redirect(url_for('auth.perfil_senha'))

    if nova_senha != confirm_nova_senha:
        flash('A nova senha deve ser digitada duas vezes de forma idêntica.', 'error')
        return redirect(url_for('auth.perfil_senha'))

    if senha_atual == nova_senha:
        flash('A nova senha deve ser diferente da senha atual.', 'error')
        return redirect(url_for('auth.perfil_senha'))

    # Validar força da nova senha
    is_valid, errors = PasswordValidator.validate(nova_senha)
    if not is_valid:
        for error in errors:
            flash(f'Erro na nova senha: {error}', 'error')
        return redirect(url_for('auth.perfil_senha'))

    # Atualizar senha
    current_user.password = PasswordValidator.hash_password(nova_senha)
    db.session.commit()

    registrar_evento(
        tipo_evento='senha_alterada',
        descricao=f'Senha alterada com sucesso',
        usuario_responsavel=current_user.username
    )

    flash('Senha atualizada com sucesso com segurança reforçada.', 'success')
    return redirect(url_for('auth.perfil_senha'))

@auth_bp.route('/perfil/foto', methods=['GET', 'POST'])
@login_required
def perfil_foto():
    """Upload de foto de perfil do usuário"""
    if not session.get('perfil_verified'):
        flash('Por favor, reautentique para acessar o perfil.', 'error')
        return redirect(url_for('auth.perfil'))

    if request.method == 'GET':
        return render_template('profile_photo.html', usuario=current_user.username, foto_perfil=current_user.foto_perfil)

    import os
    from werkzeug.utils import secure_filename

    # Configurações de upload
    UPLOAD_FOLDER = os.path.join('static', 'uploads', 'avatars')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    # Criar pasta se não existir
    upload_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', UPLOAD_FOLDER)
    upload_path = os.path.abspath(upload_path)
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)

    # Verificar se arquivo foi enviado
    if 'foto_perfil' not in request.files:
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('auth.perfil_foto'))

    file = request.files['foto_perfil']

    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('auth.perfil_foto'))

    if not allowed_file(file.filename):
        flash('Formato de arquivo não permitido. Use PNG, JPG, JPEG ou GIF.', 'error')
        return redirect(url_for('auth.perfil_foto'))

    # Verificar tamanho do arquivo
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        flash('Arquivo muito grande. Tamanho máximo: 2MB.', 'error')
        return redirect(url_for('auth.perfil_foto'))

    # Gerar nome único para o arquivo
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    filename = f"user_{current_user.id}_{int(datetime.now().timestamp())}{ext}"

    try:
        # Remover foto antiga se existir
        if current_user.foto_perfil:
            old_file = os.path.join(upload_path, current_user.foto_perfil)
            if os.path.exists(old_file):
                os.remove(old_file)

        # Salvar arquivo
        file.save(os.path.join(upload_path, filename))

        # Atualizar banco de dados
        current_user.foto_perfil = filename
        db.session.commit()

        registrar_evento(
            tipo_evento='foto_perfil_atualizada',
            descricao=f'Foto de perfil atualizada',
            usuario_responsavel=current_user.username
        )

        flash('Foto de perfil atualizada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao salvar foto: {str(e)}', 'error')

    return redirect(url_for('auth.perfil_foto'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        mensagem = request.form.get('mensagem', '').strip()

        if not username:
            flash('Informe o nome de usuário para solicitar a redefinição.', 'error')
            return redirect(url_for('auth.forgot_password'))

        user = User.query.filter_by(username=username).first()
        if user:
            texto = f'Esqueci a senha - usuário "{user.username}" solicita redefinição.'
            if mensagem:
                texto += f' Detalhes: {mensagem}'

            chamada = Chamada(id_usuario=user.id, mensagem=texto)
            db.session.add(chamada)
            db.session.commit()

            email_ok, email_error = _enviar_emails_senha_esquecida(user, texto)

            registrar_evento(
                tipo_evento='senha_esquecida',
                descricao=f'Chamado de redefinição de senha solicitado para "{user.username}"',
                usuario_responsavel='Sistema'
            )

        # Sempre mostrar a mesma mensagem, exista ou não o usuário
        flash('Se o usuário informado existir, um chamado foi registrado e um administrador irá analisar em breve.', 'success')
        return redirect(url_for('auth.forgot_password'))

    return render_template('forgot_password.html')

@auth_bp.route('/user-files')
@login_required
def user_files():
    """Página para listar arquivos salvos do usuário"""
    # Diretórios onde arquivos podem estar salvos
    upload_folders = [
        os.path.join('static', 'uploads', 'documentos'),
        os.path.join('static', 'uploads', 'chamadas')
    ]
    
    files = []
    
    # Usar o diretório raiz da aplicação (onde app.py está)
    if current_app.root_path:
        app_root = current_app.root_path
    else:
        app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    for folder in upload_folders:
        folder_path = os.path.join(app_root, folder)
        # Criar diretório se não existir
        os.makedirs(folder_path, exist_ok=True)
        
        try:
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    files.append({
                        'name': filename,
                        'path': folder,
                        'size': os.path.getsize(file_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
                    })
        except Exception as e:
            current_app.logger.error(f'Erro ao ler pasta {folder}: {str(e)}')
    
    # Ordenar por data modificada (mais recente primeiro)
    files.sort(key=lambda x: x['modified'], reverse=True)
    
    return render_template('user_files.html', usuario=current_user.username, files=files)

@auth_bp.route('/download/<path:filename>')
@login_required
def download_file(filename):
    # Diretórios onde arquivos podem estar salvos
    allowed_folders = [
        os.path.join('static', 'uploads', 'documentos'),
        os.path.join('static', 'uploads', 'chamadas')
    ]

    # Usar o diretório raiz da aplicação (onde app.py está)
    if current_app.root_path:
        app_root = current_app.root_path
    else:
        app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Verificar se o arquivo está em um dos diretórios permitidos
    for folder in allowed_folders:
        folder_path = os.path.join(app_root, folder)
        file_path = os.path.join(folder_path, filename)

        # Normalizar caminhos para comparação segura
        abs_file_path = os.path.abspath(file_path)
        abs_folder_path = os.path.abspath(folder_path)

        # Verificar se o caminho é válido e seguro (dentro da pasta permitida)
        if abs_file_path.startswith(abs_folder_path) and os.path.isfile(abs_file_path):
            # Verificar propriedade do arquivo (usuário não-admin só pode baixar arquivos próprios)
            if not current_user.is_admin:
                # Padrões de nome: {user_id}_{timestamp}_{nome} ou chamada_{user_id}_{uuid}_{nome}
                user_prefix = f"{current_user.id}_"
                chamada_prefix = f"chamada_{current_user.id}_"
                if not (filename.startswith(user_prefix) or filename.startswith(chamada_prefix)):
                    flash('Você não tem permissão para baixar este arquivo.', 'error')
                    return redirect(url_for('auth.user_files'))

            try:
                registrar_evento(
                    tipo_evento='arquivo_baixado',
                    descricao=f'Arquivo baixado: {filename}',
                    usuario_responsavel=current_user.username
                )
                return send_file(abs_file_path, as_attachment=True)
            except Exception as e:
                current_app.logger.error(f'Erro ao fazer download de {abs_file_path}: {str(e)}')
                flash(f'Erro ao baixar arquivo: {str(e)}', 'error')
                return redirect(url_for('auth.user_files'))

    current_app.logger.warning(f'Tentativa de download de arquivo não encontrado: {filename}')
    flash('Arquivo não encontrado.', 'error')
    return redirect(url_for('auth.user_files'))
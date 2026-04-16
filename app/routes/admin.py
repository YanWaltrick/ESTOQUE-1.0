from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.database import db
from app.models import User, Historico
from app.auth import require_role, require_permission
from app.auth.security import PasswordValidator, validate_username
from app.utils import registrar_evento

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@login_required
@require_role('admin')
def before_admin_request():
    """Proteger todas as rotas admin"""
    pass


# ============ GERENCIAMENTO DE USUÁRIOS ============

@admin_bp.route('/users', methods=['GET'])
@require_permission('manage_users')
def listar_usuarios():
    """Listar todos os usuários"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    usuarios_page = User.query.paginate(page=page, per_page=per_page)
    
    return render_template('admin/users.html', usuarios=usuarios_page)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@require_permission('create_user')
def criar_usuario():
    """Criar novo usuário"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'usuario')
        area = request.form.get('area', '').strip()
        localizacao = request.form.get('localizacao', '').strip()
        
        # Validações
        is_valid_user, error_msg = validate_username(username)
        if not is_valid_user:
            flash(f'Erro no nome de usuário: {error_msg}', 'error')
            return redirect(url_for('admin.criar_usuario'))
        
        if User.query.filter_by(username=username).first():
            flash('Usuário com este nome já existe.', 'error')
            return redirect(url_for('admin.criar_usuario'))
        
        is_valid_pass, errors_pass = PasswordValidator.validate(password)
        if not is_valid_pass:
            for error in errors_pass:
                flash(f'Erro na senha: {error}', 'error')
            return redirect(url_for('admin.criar_usuario'))
        
        if role not in ['admin', 'usuario']:
            flash('Role inválido. Escolha entre admin ou usuario.', 'error')
            return redirect(url_for('admin.criar_usuario'))
        
        # Criar novo usuário
        novo_usuario = User(
            username=username,
            password=PasswordValidator.hash_password(password),
            role=role,
            area=area,
            localizacao=localizacao
        )
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        registrar_evento(
            tipo_evento='usuario_criado',
            descricao=f'Novo usuário criado: "{username}" com role "{role}"',
            usuario_responsavel=current_user.username
        )
        
        flash(f'Usuário "{username}" criado com sucesso.', 'success')
        return redirect(url_for('admin.listar_usuarios'))
    
    return render_template('admin/user_form.html', mode='create')


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@require_permission('manage_users')
def editar_usuario(user_id):
    """Editar usuário existente"""
    usuario = User.query.get_or_404(user_id)
    
    # Não permitir editar a si mesmo (segurança)
    if usuario.id == current_user.id and request.method == 'POST':
        flash('Você não pode editar sua própria conta aqui. Use a página de perfil.', 'error')
        return redirect(url_for('admin.listar_usuarios'))
    
    if request.method == 'POST':
        role = request.form.get('role', usuario.role)
        area = request.form.get('area', usuario.area).strip()
        localizacao = request.form.get('localizacao', usuario.localizacao).strip()
        ativo = request.form.get('ativo') == 'on'
        
        if role not in ['admin', 'usuario']:
            flash('Role inválido. Escolha entre admin ou usuario.', 'error')
            return redirect(url_for('admin.editar_usuario', user_id=user_id))
        
        usuario.role = role
        usuario.area = area
        usuario.localizacao = localizacao
        usuario.ativo = ativo
        
        db.session.commit()
        
        registrar_evento(
            tipo_evento='usuario_editado',
            descricao=f'Usuário "{usuario.username}" editado - role: "{role}", ativo: {ativo}',
            usuario_responsavel=current_user.username
        )
        
        flash(f'Usuário "{usuario.username}" atualizado com sucesso.', 'success')
        return redirect(url_for('admin.listar_usuarios'))
    
    return render_template('admin/user_edit.html', usuario=usuario)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@require_permission('delete_user')
def deletar_usuario(user_id):
    """Deletar um usuário"""
    usuario = User.query.get_or_404(user_id)
    
    # Não permitir deletar a si mesmo
    if usuario.id == current_user.id:
        return jsonify({'success': False, 'message': 'Você não pode deletar sua própria conta.'}), 403
    
    # Não permitir deletar o último admin (segurança)
    if usuario.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            return jsonify({'success': False, 'message': 'Não é possível deletar o último administrador.'}), 403
    
    username = usuario.username
    db.session.delete(usuario)
    db.session.commit()
    
    registrar_evento(
        tipo_evento='usuario_deletado',
        descricao=f'Usuário "{username}" foi deletado',
        usuario_responsavel=current_user.username
    )
    
    return jsonify({'success': True, 'message': f'Usuário "{username}" deletado com sucesso.'})


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@require_permission('manage_users')
def resetar_senha_usuario(user_id):
    """Resetar senha de um usuário (admin tool)"""
    usuario = User.query.get_or_404(user_id)
    nova_senha = request.form.get('nova_senha', '').strip()
    
    if not nova_senha:
        return jsonify({'success': False, 'message': 'Nova senha não pode estar vazia.'}), 400
    
    is_valid, errors = PasswordValidator.validate(nova_senha)
    if not is_valid:
        return jsonify({'success': False, 'message': '; '.join(errors)}), 400
    
    usuario.password = PasswordValidator.hash_password(nova_senha)
    usuario.tentativas_login_falhas = 0
    usuario.bloqueado_ate = None
    db.session.commit()
    
    registrar_evento(
        tipo_evento='senha_resetada',
        descricao=f'Senha do usuário "{usuario.username}" foi resetada pelo admin',
        usuario_responsavel=current_user.username
    )
    
    return jsonify({'success': True, 'message': f'Senha de "{usuario.username}" foi resetada.'})


@admin_bp.route('/users/<int:user_id>/toggle-block', methods=['POST'])
@require_permission('manage_users')
def toggle_bloqueio_usuario(user_id):
    """Bloquear/desbloquear um usuário"""
    usuario = User.query.get_or_404(user_id)
    
    if usuario.id == current_user.id:
        return jsonify({'success': False, 'message': 'Você não pode bloquear a sua própria conta.'}), 403
    
    usuario.ativo = not usuario.ativo
    acacao = "desbloqueado" if usuario.ativo else "bloqueado"
    db.session.commit()
    
    registrar_evento(
        tipo_evento='usuario_bloqueado' if not usuario.ativo else 'usuario_desbloqueado',
        descricao=f'Usuário "{usuario.username}" foi {acacao}',
        usuario_responsavel=current_user.username
    )
    
    return jsonify({'success': True, 'message': f'Usuário "{usuario.username}" foi {acacao}.'})


# ============ AUDITORIA ============

@admin_bp.route('/audit-log', methods=['GET'])
@require_permission('view_audit_log')
def audit_log():
    """Visualizar log de auditoria"""
    page = request.args.get('page', 1, type=int)
    tipo_evento = request.args.get('tipo', '')
    usuario = request.args.get('usuario', '')
    
    query = Historico.query
    
    if tipo_evento:
        query = query.filter_by(tipo_evento=tipo_evento)
    
    if usuario:
        query = query.filter_by(usuario_responsavel=usuario)
    
    eventos = query.order_by(Historico.data_evento.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/audit_log.html', eventos=eventos)


# ============ DASHBOARD ============

@admin_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Dashboard administrativo"""
    total_usuarios = User.query.count()
    usuarios_ativos = User.query.filter_by(ativo=True).count()
    usuarios_bloqueados = User.query.filter_by(ativo=False).count()
    
    admins = User.query.filter_by(role='admin').count()
    
    eventos_recentes = Historico.query.order_by(Historico.data_evento.desc()).limit(10).all()
    
    stats = {
        'total_usuarios': total_usuarios,
        'usuarios_ativos': usuarios_ativos,
        'usuarios_bloqueados': usuarios_bloqueados,
        'admins': admins,
        'eventos_recentes': eventos_recentes
    }
    
    return render_template('admin/dashboard.html', stats=stats)
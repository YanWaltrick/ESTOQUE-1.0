from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.database import db
from app.models import User, Historico, DocumentoUsuario, ItemRecebido
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


@admin_bp.route('/usuarios', methods=['GET'])
def usuarios_pagina():
    """Página exclusiva com lista visual de usuários."""
    usuarios = User.query.order_by(User.ativo.desc(), User.role.desc(), User.username.asc()).all()
    return render_template('admin/usuarios.html', usuarios=usuarios)


# ============ GERENCIAMENTO DE DOCUMENTOS ============

@admin_bp.route('/usuarios/<int:user_id>/documentos/upload', methods=['POST'])
def upload_documento_usuario(user_id):
    """Upload de documento para um usuário"""
    import os
    from werkzeug.utils import secure_filename
    from datetime import datetime
    
    usuario = User.query.get_or_404(user_id)
    
    # Validar arquivo
    if 'arquivo' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo foi enviado.'}), 400
    
    arquivo = request.files['arquivo']
    if arquivo.filename == '':
        return jsonify({'success': False, 'message': 'Arquivo não selecionado.'}), 400
    
    # Obter dados do formulário
    nome_documento = request.form.get('nome', '').strip()
    descricao = request.form.get('descricao', '').strip()
    
    if not nome_documento:
        return jsonify({'success': False, 'message': 'Nome do documento é obrigatório.'}), 400
    
    # Validações de arquivo
    EXTENSOES_PERMITIDAS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'jpeg', 'png', 'gif'}
    TAMANHO_MAXIMO = 10 * 1024 * 1024  # 10MB
    
    # Verificar extensão
    if not ('.' in arquivo.filename):
        return jsonify({'success': False, 'message': 'Arquivo sem extensão.'}), 400
    
    extensao = arquivo.filename.rsplit('.', 1)[1].lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        return jsonify({'success': False, 'message': f'Tipo de arquivo não permitido. Extensões aceitas: {", ".join(EXTENSOES_PERMITIDAS)}'}), 400
    
    # Verificar tamanho
    arquivo.seek(0, os.SEEK_END)
    tamanho = arquivo.tell()
    arquivo.seek(0)
    
    if tamanho > TAMANHO_MAXIMO:
        return jsonify({'success': False, 'message': f'Arquivo muito grande. Máximo: 10MB. Seu arquivo: {tamanho / (1024*1024):.2f}MB'}), 400
    
    if tamanho == 0:
        return jsonify({'success': False, 'message': 'Arquivo vazio.'}), 400
    
    # Criar pasta se não existir
    pasta_documentos = os.path.join('static', 'uploads', 'documentos')
    if not os.path.exists(pasta_documentos):
        os.makedirs(pasta_documentos, exist_ok=True)
    
    # Gerar nome único para o arquivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_arquivo_seguro = secure_filename(f"{usuario.id}_{timestamp}_{arquivo.filename}")
    caminho_arquivo = os.path.join(pasta_documentos, nome_arquivo_seguro)
    
    try:
        # Salvar arquivo
        arquivo.save(caminho_arquivo)
        
        # Criar registro no banco de dados
        novo_documento = DocumentoUsuario(
            id_usuario=usuario.id,
            nome_documento=nome_documento,
            arquivo=nome_arquivo_seguro,
            tipo_arquivo=extensao,
            tamanho_arquivo=tamanho,
            usuario_enviador=current_user.username,
            descricao=descricao if descricao else None
        )
        
        db.session.add(novo_documento)
        db.session.commit()
        
        # Registrar no auditoria
        registrar_evento(
            tipo_evento='documento_usuario_enviado',
            descricao=f'Documento "{nome_documento}" enviado para o usuário "{usuario.username}"',
            usuario_responsavel=current_user.username,
            detalhes=f'Arquivo: {nome_arquivo_seguro}, Tamanho: {tamanho} bytes'
        )
        
        return jsonify({
            'success': True,
            'message': f'Documento "{nome_documento}" enviado com sucesso!',
            'documento': novo_documento.to_dict()
        })
    
    except Exception as e:
        # Remover arquivo se algo deu errado no banco de dados
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)
        
        return jsonify({'success': False, 'message': f'Erro ao salvar documento: {str(e)}'}), 500


@admin_bp.route('/usuarios/documentos/<int:documento_id>/download', methods=['GET'])
def download_documento(documento_id):
    """Download de documento do usuário"""
    from flask import send_file
    import os
    
    documento = DocumentoUsuario.query.get_or_404(documento_id)
    
    # Verificar permissões: apenas admin pode fazer download
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permissão negada.'}), 403
    
    caminho_arquivo = os.path.join('static', 'uploads', 'documentos', documento.arquivo)
    
    if not os.path.exists(caminho_arquivo):
        return jsonify({'success': False, 'message': 'Arquivo não encontrado.'}), 404
    
    try:
        return send_file(
            caminho_arquivo,
            as_attachment=True,
            download_name=documento.arquivo,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao fazer download: {str(e)}'}), 500


@admin_bp.route('/usuarios/<int:user_id>/documentos', methods=['GET'])
def listar_documentos_usuario(user_id):
    """Listar documentos de um usuário"""
    usuario = User.query.get_or_404(user_id)
    documentos = DocumentoUsuario.query.filter_by(id_usuario=user_id).order_by(DocumentoUsuario.data_criacao.desc()).all()
    
    return jsonify({
        'success': True,
        'usuario': usuario.username,
        'documentos': [doc.to_dict() for doc in documentos]
    })


# ============ GERENCIAMENTO DE ITENS RECEBIDOS ============

@admin_bp.route('/usuarios/<int:user_id>/itens-recebidos', methods=['GET'])
def listar_itens_recebidos(user_id):
    """Listar itens recebidos de um usuário separados por tipo"""
    usuario = User.query.get_or_404(user_id)
    
    itens_entrada = ItemRecebido.query.filter_by(
        id_usuario=user_id,
        tipo_recebimento='entrada'
    ).order_by(ItemRecebido.data_criacao.desc()).all()
    
    itens_posteriormente = ItemRecebido.query.filter_by(
        id_usuario=user_id,
        tipo_recebimento='posteriormente'
    ).order_by(ItemRecebido.data_criacao.desc()).all()
    
    return jsonify({
        'success': True,
        'usuario': usuario.username,
        'itens_entrada': [item.to_dict() for item in itens_entrada],
        'itens_posteriormente': [item.to_dict() for item in itens_posteriormente]
    })


@admin_bp.route('/usuarios/<int:user_id>/itens-recebidos/adicionar', methods=['POST'])
def adicionar_item_recebido(user_id):
    """Adicionar novo item recebido para um usuário"""
    usuario = User.query.get_or_404(user_id)
    
    descricao_item = request.form.get('descricao', '').strip()
    tipo_recebimento = request.form.get('tipo', 'entrada').strip()
    
    if not descricao_item:
        return jsonify({'success': False, 'message': 'Descrição do item é obrigatória.'}), 400
    
    if tipo_recebimento not in ['entrada', 'posteriormente']:
        return jsonify({'success': False, 'message': 'Tipo de recebimento inválido.'}), 400
    
    novo_item = ItemRecebido(
        id_usuario=user_id,
        descricao_item=descricao_item,
        tipo_recebimento=tipo_recebimento,
        usuario_responsavel=current_user.username
    )
    
    db.session.add(novo_item)
    db.session.commit()
    
    registrar_evento(
        tipo_evento='item_recebido_adicionado',
        descricao=f'Item "{descricao_item}" adicionado para "{usuario.username}" (tipo: {tipo_recebimento})',
        usuario_responsavel=current_user.username
    )
    
    return jsonify({
        'success': True,
        'message': 'Item adicionado com sucesso!',
        'item': novo_item.to_dict()
    })


@admin_bp.route('/usuarios/itens-recebidos/<int:item_id>/editar', methods=['PUT'])
def editar_item_recebido(item_id):
    """Editar item recebido"""
    item = ItemRecebido.query.get_or_404(item_id)
    
    data = request.get_json()
    descricao_item = data.get('descricao', '').strip()
    tipo_recebimento = data.get('tipo', item.tipo_recebimento).strip()
    
    if not descricao_item:
        return jsonify({'success': False, 'message': 'Descrição do item é obrigatória.'}), 400
    
    if tipo_recebimento not in ['entrada', 'posteriormente']:
        return jsonify({'success': False, 'message': 'Tipo de recebimento inválido.'}), 400
    
    item.descricao_item = descricao_item
    item.tipo_recebimento = tipo_recebimento
    db.session.commit()
    
    registrar_evento(
        tipo_evento='item_recebido_editado',
        descricao=f'Item ID {item_id} foi editado: "{descricao_item}" (tipo: {tipo_recebimento})',
        usuario_responsavel=current_user.username
    )
    
    return jsonify({
        'success': True,
        'message': 'Item atualizado com sucesso!',
        'item': item.to_dict()
    })


@admin_bp.route('/usuarios/itens-recebidos/<int:item_id>/deletar', methods=['DELETE'])
def deletar_item_recebido(item_id):
    """Deletar item recebido"""
    item = ItemRecebido.query.get_or_404(item_id)
    id_usuario = item.id_usuario
    descricao = item.descricao_item
    
    db.session.delete(item)
    db.session.commit()
    
    registrar_evento(
        tipo_evento='item_recebido_deletado',
        descricao=f'Item "{descricao}" foi deletado',
        usuario_responsavel=current_user.username
    )
    
    return jsonify({
        'success': True,
        'message': 'Item deletado com sucesso!'
    })
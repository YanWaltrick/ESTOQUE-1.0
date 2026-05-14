import os
import json
from datetime import datetime, timezone, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app.database import db
from app.models import User, Historico, DocumentoUsuario, ItemRecebido, TermoEntrega
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
    
    return render_template('admin/usuarios.html', usuarios=usuarios_page)


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
        empresa = request.form.get('empresa', '').strip()
        cnpj = request.form.get('cnpj', '').strip()
        endereco = request.form.get('endereco', '').strip()
        cargo = request.form.get('cargo', '').strip()
        cpf = request.form.get('cpf', '').strip()
        data_admissao_str = request.form.get('data_admissao', '').strip()
        departamento = request.form.get('departamento', '').strip()
        local_trabalho = request.form.get('local_trabalho', '').strip()
        
        # Converter data_admissao
        data_admissao = None
        if data_admissao_str:
            try:
                from datetime import datetime
                data_admissao = datetime.strptime(data_admissao_str, '%Y-%m-%d').date()
            except:
                flash('Erro ao processar a data de admissão.', 'error')
                return redirect(url_for('admin.criar_usuario'))
        
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
            localizacao=localizacao,
            empresa=empresa,
            cnpj=cnpj,
            endereco=endereco,
            cargo=cargo,
            cpf=cpf,
            data_admissao=data_admissao,
            departamento=departamento,
            local_trabalho=local_trabalho
        )
        
        db.session.add(novo_usuario)
        db.session.flush()  # Gera o ID sem fazer commit
        
        # Criar automaticamente Termo de Entrega e Responsabilidade
        termo = TermoEntrega(
            id_usuario=novo_usuario.id,
            empresa=empresa,
            cnpj=cnpj,
            endereco=endereco,
            nome_colaborador=username,
            cargo_funcao=cargo,
            cpf_cnpj=cpf,
            departamento=departamento,
            local_trabalho=local_trabalho,
            data_admissao=data_admissao
        )
        db.session.add(termo)
        db.session.commit()
        
        registrar_evento(
            tipo_evento='usuario_criado',
            descricao=f'Novo usuário criado: "{username}" com role "{role}" e Termo de Entrega gerado',
            usuario_responsavel=current_user.username
        )
        
        flash(f'Usuário "{username}" criado com sucesso e Termo de Entrega gerado.', 'success')
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
        empresa = request.form.get('empresa', usuario.empresa).strip()
        cnpj = request.form.get('cnpj', usuario.cnpj).strip()
        endereco = request.form.get('endereco', usuario.endereco).strip()
        cargo = request.form.get('cargo', usuario.cargo).strip()
        cpf = request.form.get('cpf', usuario.cpf).strip()
        data_admissao_str = request.form.get('data_admissao', '').strip()
        departamento = request.form.get('departamento', usuario.departamento).strip()
        local_trabalho = request.form.get('local_trabalho', usuario.local_trabalho).strip()
        ativo = request.form.get('ativo') == 'on'
        
        # Converter data_admissao
        data_admissao = usuario.data_admissao
        if data_admissao_str:
            try:
                from datetime import datetime
                data_admissao = datetime.strptime(data_admissao_str, '%Y-%m-%d').date()
            except:
                flash('Erro ao processar a data de admissão.', 'error')
                return redirect(url_for('admin.editar_usuario', user_id=user_id))
        
        if role not in ['admin', 'usuario']:
            flash('Role inválido. Escolha entre admin ou usuario.', 'error')
            return redirect(url_for('admin.editar_usuario', user_id=user_id))
        
        usuario.role = role
        usuario.area = area
        usuario.localizacao = localizacao
        usuario.empresa = empresa
        usuario.cnpj = cnpj
        usuario.endereco = endereco
        usuario.cargo = cargo
        usuario.cpf = cpf
        usuario.data_admissao = data_admissao
        usuario.departamento = departamento
        usuario.local_trabalho = local_trabalho
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
    pasta_documentos = os.path.join(current_app.root_path, '..', 'static', 'uploads', 'documentos')
    pasta_documentos = os.path.abspath(pasta_documentos)
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


def _caminho_documentos():
    return os.path.abspath(os.path.join(current_app.root_path, '..', 'static', 'uploads', 'documentos'))


def _caminho_documento(documento):
    return os.path.join(_caminho_documentos(), documento.arquivo)


@admin_bp.route('/usuarios/documentos/<int:documento_id>/visualizar', methods=['GET'])
def visualizar_documento(documento_id):
    """Abrir documento para pré-visualização."""
    documento = DocumentoUsuario.query.get_or_404(documento_id)

    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permissão negada.'}), 403

    caminho_arquivo = _caminho_documento(documento)

    if not os.path.exists(caminho_arquivo):
        return jsonify({'success': False, 'message': 'Arquivo não encontrado.'}), 404

    return send_file(caminho_arquivo, as_attachment=False)


@admin_bp.route('/usuarios/documentos/<int:documento_id>/download', methods=['GET'])
def download_documento(documento_id):
    """Download de documento do usuário"""
    documento = DocumentoUsuario.query.get_or_404(documento_id)
    
    # Verificar permissões: apenas admin pode fazer download
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permissão negada.'}), 403
    
    caminho_arquivo = _caminho_documento(documento)
    
    if not os.path.exists(caminho_arquivo):
        return jsonify({'success': False, 'message': 'Arquivo não encontrado.'}), 404
    
    try:
        return send_file(
            caminho_arquivo,
            as_attachment=True,
            download_name=f'{documento.nome_documento}.{documento.tipo_arquivo}',
            mimetype='application/octet-stream'
        )
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao fazer download: {str(e)}'}), 500


@admin_bp.route('/usuarios/<int:user_id>/documentos', methods=['GET'])
def listar_documentos_usuario(user_id):
    """Listar documentos de um usuário"""
    usuario = User.query.get_or_404(user_id)
    documentos = DocumentoUsuario.query.filter_by(id_usuario=user_id).order_by(DocumentoUsuario.data_criacao.desc()).all()

    documentos_json = []
    for doc in documentos:
        documento = doc.to_dict()
        documento['download_url'] = url_for('admin.download_documento', documento_id=doc.id_documento)
        documento['preview_url'] = url_for('admin.visualizar_documento', documento_id=doc.id_documento)
        documento['pode_visualizar'] = doc.tipo_arquivo.lower() in {'pdf', 'jpg', 'jpeg', 'png', 'gif'}
        documentos_json.append(documento)
    
    return jsonify({
        'success': True,
        'usuario': usuario.username,
        'documentos': documentos_json
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


# ============ GERENCIAMENTO DE TERMOS DE ENTREGA ============

@admin_bp.route('/usuarios/<int:user_id>/termo-entrega', methods=['GET'])
def listar_termo_entrega(user_id):
    """Recuperar Termo de Entrega e Responsabilidade de um usuário"""
    usuario = User.query.get_or_404(user_id)
    termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()

    # If termo doesn't exist, return an empty termo structure (modal will allow creating/updating)
    if not termo:
        termo_data = {
            'id': None,
            'id_usuario': usuario.id,
            'usuario': usuario.username,
            'empresa': usuario.empresa or '',
            'cnpj': usuario.cnpj or '',
            'endereco': usuario.endereco or '',
            'nome_colaborador': usuario.username,
            'cargo_funcao': usuario.cargo or '',
            'cpf_cnpj': usuario.cpf or '',
            'departamento': usuario.departamento or '',
            'local_trabalho': usuario.local_trabalho or '',
            'data_admissao': usuario.data_admissao.strftime("%Y-%m-%d") if usuario.data_admissao else None,
            'equipamentos': [],
            'data_criacao': None,
            'data_atualizacao': None,
            'assinado': False,
            'data_assinatura': None,
            'observacoes': ''
        }

        return jsonify({
            'success': True,
            'termo': termo_data
        })

    return jsonify({
        'success': True,
        'termo': termo.to_dict()
    })


@admin_bp.route('/usuarios/<int:user_id>/termo-entrega/atualizar', methods=['POST'])
def atualizar_termo_entrega(user_id):
    """Atualizar informações do Termo de Entrega"""
    usuario = User.query.get_or_404(user_id)
    termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()

    # If termo doesn't exist, create it
    if not termo:
        termo = TermoEntrega(
            id_usuario=user_id,
            empresa=request.form.get('empresa', usuario.empresa or ''),
            cnpj=request.form.get('cnpj', usuario.cnpj or ''),
            endereco=request.form.get('endereco', usuario.endereco or ''),
            nome_colaborador=usuario.username,
            cargo_funcao=request.form.get('cargo_funcao', usuario.cargo or ''),
            cpf_cnpj=request.form.get('cpf_cnpj', usuario.cpf or ''),
            departamento=request.form.get('departamento', usuario.departamento or ''),
            local_trabalho=request.form.get('local_trabalho', usuario.local_trabalho or ''),
            data_admissao=usuario.data_admissao
        )
        db.session.add(termo)

    # Atualizar informações do termo
    termo.empresa = request.form.get('empresa', termo.empresa or '').strip()
    termo.cnpj = request.form.get('cnpj', termo.cnpj or '').strip()
    termo.endereco = request.form.get('endereco', termo.endereco or '').strip()
    termo.cargo_funcao = request.form.get('cargo_funcao', termo.cargo_funcao or '').strip()
    termo.departamento = request.form.get('departamento', termo.departamento or '').strip()
    termo.local_trabalho = request.form.get('local_trabalho', termo.local_trabalho or '').strip()

    observacoes = request.form.get('observacoes', '').strip()
    termo.observacoes = observacoes

    db.session.commit()

    registrar_evento(
        tipo_evento='termo_entrega_atualizado',
        descricao=f'Termo de Entrega do usuário "{usuario.username}" foi atualizado',
        usuario_responsavel=current_user.username
    )

    return jsonify({
        'success': True,
        'message': 'Termo atualizado com sucesso!',
        'termo': termo.to_dict()
    })


@admin_bp.route('/usuarios/<int:user_id>/termo-entrega/equipamentos/adicionar', methods=['POST'])
def adicionar_equipamento_termo(user_id):
    """Adicionar equipamento ao Termo de Entrega"""
    usuario = User.query.get_or_404(user_id)
    termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()

    # If termo does not exist, create it so we can add equipment
    if not termo:
        termo = TermoEntrega(
            id_usuario=user_id,
            empresa=usuario.empresa or '',
            cnpj=usuario.cnpj or '',
            endereco=usuario.endereco or '',
            nome_colaborador=usuario.username,
            cargo_funcao=usuario.cargo or '',
            cpf_cnpj=usuario.cpf or '',
            departamento=usuario.departamento or '',
            local_trabalho=usuario.local_trabalho or '',
            data_admissao=usuario.data_admissao
        )
        db.session.add(termo)

    descricao = request.form.get('descricao', '').strip()
    marca = request.form.get('marca', '').strip()
    modelo = request.form.get('modelo', '').strip()
    estado = request.form.get('estado', 'Bom').strip()

    if not descricao:
        return jsonify({
            'success': False,
            'message': 'Descrição do equipamento é obrigatória.'
        }), 400

    # Carregar equipamentos existentes
    equipamentos = json.loads(termo.equipamentos) if termo.equipamentos else []

    # Adicionar novo equipamento
    novo_equipamento = {
        'id': (equipamentos[-1]['id'] + 1) if equipamentos else 1,
        'descricao': descricao,
        'marca': marca,
        'modelo': modelo,
        'estado': estado,
        'data_entrega': datetime.now(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M:%S")
    }
    equipamentos.append(novo_equipamento)

    # Salvar equipamentos atualizados
    termo.equipamentos = json.dumps(equipamentos)
    db.session.commit()

    registrar_evento(
        tipo_evento='equipamento_adicionado_termo',
        descricao=f'Equipamento "{descricao}" adicionado ao Termo de Entrega de "{usuario.username}"',
        usuario_responsavel=current_user.username
    )

    return jsonify({
        'success': True,
        'message': 'Equipamento adicionado com sucesso!',
        'equipamento': novo_equipamento
    })


@admin_bp.route('/usuarios/<int:user_id>/termo-entrega/equipamentos/<int:eq_id>/deletar', methods=['DELETE'])
def deletar_equipamento_termo(user_id, eq_id):
    """Deletar equipamento do Termo de Entrega"""
    usuario = User.query.get_or_404(user_id)
    termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()

    if not termo:
        return jsonify({
            'success': False,
            'message': 'Nenhum termo encontrado para este usuário.'
        }), 404

    # Carregar equipamentos
    equipamentos = json.loads(termo.equipamentos) if termo.equipamentos else []

    # Procurar e remover equipamento
    equipamento_removido = None
    for i, eq in enumerate(equipamentos):
        if eq.get('id') == eq_id:
            equipamento_removido = equipamentos.pop(i)
            break

    if not equipamento_removido:
        return jsonify({
            'success': False,
            'message': 'Equipamento não encontrado.'
        }), 404

    # Salvar lista atualizada
    termo.equipamentos = json.dumps(equipamentos)
    db.session.commit()

    registrar_evento(
        tipo_evento='equipamento_removido_termo',
        descricao=f'Equipamento "{equipamento_removido.get("descricao")}" removido do Termo de Entrega de "{usuario.username}"',
        usuario_responsavel=current_user.username
    )

    return jsonify({
        'success': True,
        'message': 'Equipamento removido com sucesso!'
    })


@admin_bp.route('/usuarios/<int:user_id>/termo-entrega/assinar', methods=['POST'])
def assinar_termo_entrega(user_id):
    """Marcar Termo de Entrega como assinado"""
    usuario = User.query.get_or_404(user_id)
    termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()

    from datetime import datetime, timezone, timedelta

    # If termo doesn't exist, create it and mark signed
    if not termo:
        termo = TermoEntrega(
            id_usuario=user_id,
            empresa=usuario.empresa or '',
            cnpj=usuario.cnpj or '',
            endereco=usuario.endereco or '',
            nome_colaborador=usuario.username,
            cargo_funcao=usuario.cargo or '',
            cpf_cnpj=usuario.cpf or '',
            departamento=usuario.departamento or '',
            local_trabalho=usuario.local_trabalho or '',
            data_admissao=usuario.data_admissao
        )
        db.session.add(termo)

    termo.assinado = True
    termo.data_assinatura = datetime.now(timezone(timedelta(hours=-3)))
    db.session.commit()

    registrar_evento(
        tipo_evento='termo_entrega_assinado',
        descricao=f'Termo de Entrega do usuário "{usuario.username}" foi assinado',
        usuario_responsavel=current_user.username
    )

    return jsonify({
        'success': True,
        'message': 'Termo marcado como assinado com sucesso!',
        'termo': termo.to_dict()
    })


@admin_bp.route('/usuarios/<int:user_id>/termo-entrega/exportar', methods=['POST'])
def exportar_termo_pdf(user_id):
    """Gerar arquivo .pdf do Termo preenchido e salvar em uploads/documentos"""
    usuario = User.query.get_or_404(user_id)
    termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()

    # Use data from termo if present, otherwise from usuario
    dados = termo.to_dict() if termo else {
        'empresa': usuario.empresa or '',
        'cnpj': usuario.cnpj or '',
        'endereco': usuario.endereco or '',
        'nome_colaborador': usuario.username,
        'cargo_funcao': usuario.cargo or '',
        'cpf_cnpj': usuario.cpf or '',
        'data_admissao': usuario.data_admissao.strftime("%d/%m/%Y") if usuario.data_admissao else '',
        'departamento': usuario.departamento or '',
        'local_trabalho': usuario.local_trabalho or '',
        'equipamentos': []
    }

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.platypus import Paragraph, Table, TableStyle
        from reportlab.pdfgen import canvas
    except Exception:
        return jsonify({'success': False, 'message': 'Dependência reportlab não instalada. Rode: pip install reportlab'}), 500

    import os
    from datetime import datetime
    from textwrap import wrap

    equipamentos = dados.get('equipamentos') or []

    def draw_wrapped_text(pdf, text, x, y, max_width, font_name='Times-Roman', font_size=10, leading=13):
        pdf.setFont(font_name, font_size)
        words = text.split()
        lines = []
        current = ''
        for word in words:
            candidate = f'{current} {word}'.strip()
            if stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        for line in lines:
            pdf.drawString(x, y, line)
            y -= leading
        return y

    # Salvar arquivo em static/uploads/documentos
    pasta = os.path.abspath(os.path.join(current_app.root_path, '..', 'static', 'uploads', 'documentos'))
    os.makedirs(pasta, exist_ok=True)
    nome_arquivo = f'termo_{usuario.id}.pdf'
    caminho = os.path.join(pasta, nome_arquivo)

    pdf = canvas.Canvas(caminho, pagesize=A4)
    width, height = A4
    left = 18 * mm
    right = width - 18 * mm
    top = height - 18 * mm
    y = top

    pdf.setTitle('Termo de Entrega e Responsabilidade')

    pdf.setFont('Times-Bold', 11)
    title = 'TERMO DE ENTREGA E RESPONSABILIDADE PELO USO DE EQUIPAMENTOS DA EMPRESA'
    pdf.drawCentredString(width / 2, y, title)
    y -= 22

    pdf.setFont('Times-Roman', 10)

    campos = [
        ('Empresa', dados.get('empresa', '')),
        ('CNPJ', dados.get('cnpj', '')),
        ('Endereço', dados.get('endereco', '')),
        ('Colaborador', dados.get('nome_colaborador', '')),
        ('Cargo/Função (se aplicável)', dados.get('cargo_funcao', '')),
        ('CPF/CNPJ', dados.get('cpf_cnpj', '')),
        ('Data de Admissão (se aplicável)', dados.get('data_admissao', '')),
        ('Departamento (se aplicável)', dados.get('departamento', '')),
        ('Local de trabalho (se aplicável)', dados.get('local_trabalho', '')),
    ]

    label_x = left
    value_x = left + 47 * mm
    line_x1 = value_x
    line_x2 = right - 1 * mm
    for label, value in campos:
        pdf.drawString(label_x, y, f'{label}:')
        pdf.line(line_x1, y - 1.5, line_x2, y - 1.5)
        if value:
            pdf.drawString(value_x + 2, y + 0.5, str(value))
        y -= 13

    y -= 6
    pdf.setFont('Times-Bold', 10)
    pdf.drawString(left, y, '1. OBJETO')
    y -= 12
    pdf.setFont('Times-Roman', 10)
    y = draw_wrapped_text(
        pdf,
        'O presente Termo tem por objeto formalizar a entrega, posse e responsabilidade do colaborador quanto ao uso, guarda, conservação e devolução dos equipamentos, dispositivos, acessórios e demais bens de propriedade da empresa, fornecidos para a execução de suas atividades profissionais.',
        left,
        y,
        right - left,
        font_size=9.5,
        leading=12
    ) - 8

    pdf.setFont('Times-Bold', 10)
    pdf.drawString(left, y, '2. EQUIPAMENTOS ENTREGUES')
    y -= 12
    pdf.setFont('Times-Roman', 10)
    pdf.drawString(left, y, 'A empresa declara ter fornecido os seguintes itens ao colaborador, elencado no preâmbulo:')
    y -= 20

    data = [['Equipamento / Acessório', 'Marca', 'Modelo', 'Estado', 'Data\nEntrega', 'Valor\nAproximado']]
    for eq in equipamentos[:8]:
        data.append([
            eq.get('descricao', ''),
            eq.get('marca', ''),
            eq.get('modelo', ''),
            eq.get('estado', ''),
            eq.get('data_entrega', ''),
            ''
        ])

    while len(data) < 9:
        data.append(['', '', '', '', '', ''])

    table = Table(data, colWidths=[30 * mm, 24 * mm, 24 * mm, 22 * mm, 20 * mm, 20 * mm])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
    ]))

    tw, th = table.wrapOn(pdf, width - 2 * left, y)
    table.drawOn(pdf, left, y - th)
    y = y - th - 15

    pdf.setFont('Times-Bold', 10)
    pdf.drawString(left, y, '3. CHECKLIST DE ENTREGA')
    y -= 13
    pdf.setFont('Times-Roman', 10)
    y = draw_wrapped_text(
        pdf,
        'Considerando o disposto na cláusula anterior, o colaborador declara, nesta data e por meio do checklist abaixo colacionado, ter recebido, na presente data, os seguintes itens de propriedade da empresa, para uso exclusivamente profissional:',
        left,
        y,
        right - left,
        font_size=9.5,
        leading=12
    )

    pdf.showPage()
    pdf.save()

    tamanho = os.path.getsize(caminho)

    usuario_enviador = getattr(current_user, 'username', None) or getattr(current_user, 'name', None) or 'sistema'

    # Criar ou atualizar registro DocumentoUsuario
    novo_doc = DocumentoUsuario.query.filter_by(
        id_usuario=usuario.id,
        nome_documento='Termo de Entrega'
    ).first()

    if not novo_doc:
        novo_doc = DocumentoUsuario(
            id_usuario=usuario.id,
            nome_documento='Termo de Entrega',
            arquivo=nome_arquivo,
            tipo_arquivo='pdf',
            tamanho_arquivo=tamanho,
            usuario_enviador=usuario_enviador,
            descricao='Termo de Entrega gerado automaticamente'
        )
        db.session.add(novo_doc)
    else:
        novo_doc.arquivo = nome_arquivo
        novo_doc.tipo_arquivo = 'pdf'
        novo_doc.tamanho_arquivo = tamanho
        novo_doc.usuario_enviador = usuario_enviador
        novo_doc.descricao = 'Termo de Entrega gerado automaticamente'

    db.session.commit()

    return jsonify({'success': True, 'message': 'Termo exportado e salvo nos documentos do usuário.', 'documento_id': novo_doc.id_documento})
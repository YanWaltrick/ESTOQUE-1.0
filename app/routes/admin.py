import os
import json
from datetime import datetime, timezone, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_required, current_user
from sqlalchemy import case
from app.database import db
from app.models import User, Historico, DocumentoUsuario, ItemRecebido, TermoEntrega
from app.auth import require_role, require_permission
from app.auth.security import PasswordValidator, validate_username
from app.utils import registrar_evento
from werkzeug.utils import secure_filename
from uuid import uuid4

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@login_required
@require_role('admin')
def before_admin_request():
    """Proteger todas as rotas admin"""
    pass


def _listar_usuarios_paginados(page=1, per_page=10, q='', tipo=''):
    query = User.query

    if q:
        query = query.filter(User.username.ilike(f'%{q}%'))

    if tipo in {'CLT', 'PJ'}:
        query = query.filter(User.tipo_contrato == tipo)

    return query.order_by(
        case((User.tipo_contrato == 'CLT', 0), else_=1),
        User.ativo.desc(),
        User.username.asc()
    ).paginate(page=page, per_page=per_page)


# ============ GERENCIAMENTO DE USUÁRIOS ============

@admin_bp.route('/users', methods=['GET'])
@require_permission('manage_users')
def listar_usuarios():
    """Listar todos os usuários"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    q = request.args.get('q', '').strip()
    tipo = request.args.get('tipo', '').strip().upper()

    usuarios_page = _listar_usuarios_paginados(page=page, per_page=per_page, q=q, tipo=tipo)

    return render_template('admin/usuarios.html', usuarios=usuarios_page, q=q, tipo=tipo)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@require_permission('create_user')
def criar_usuario():
    """Criar novo usuário"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'usuario')
        tipo_contrato = request.form.get('tipo_contrato', 'CLT').strip().upper()
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
        # Campos PJ
        pj_contratante = request.form.get('pj_contratante', '').strip()
        pj_contratante_cnpj = request.form.get('pj_contratante_cnpj', '').strip()
        pj_contratante_endereco = request.form.get('pj_contratante_endereco', '').strip()
        pj_contratada = request.form.get('pj_contratada', '').strip()
        pj_contratada_cnpj = request.form.get('pj_contratada_cnpj', '').strip()
        pj_data_contrato_str = request.form.get('pj_data_contrato', '').strip()
        
        # Converter data_admissao
        data_admissao = None
        if data_admissao_str:
            try:
                from datetime import datetime
                data_admissao = datetime.strptime(data_admissao_str, '%Y-%m-%d').date()
            except:
                flash('Erro ao processar a data de admissão.', 'error')
                return redirect(url_for('admin.criar_usuario'))

        # Converter data do contrato PJ
        pj_data_contrato = None
        if pj_data_contrato_str:
            try:
                from datetime import datetime
                pj_data_contrato = datetime.strptime(pj_data_contrato_str, '%Y-%m-%d').date()
            except:
                flash('Erro ao processar a data do contrato PJ.', 'error')
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

        if tipo_contrato not in ['CLT', 'PJ']:
            flash('Tipo de contrato inválido. Escolha entre CLT ou PJ.', 'error')
            return redirect(url_for('admin.criar_usuario'))
        # Validação mínima para PJ (opcional campos obrigatórios)
        if tipo_contrato == 'PJ':
            if not pj_contratante or not pj_contratante_cnpj:
                flash('Para contrato PJ, informe Contratante e CNPJ do Contratante.', 'error')
                return redirect(url_for('admin.criar_usuario'))
        
        # Criar novo usuário
        novo_usuario = User(
            username=username,
            password=PasswordValidator.hash_password(password),
            role=role,
            tipo_contrato=tipo_contrato,
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
            ,pj_contratante=pj_contratante,
            pj_contratante_cnpj=pj_contratante_cnpj,
            pj_contratante_endereco=pj_contratante_endereco,
            pj_contratada=pj_contratada,
            pj_contratada_cnpj=pj_contratada_cnpj,
            pj_data_contrato=pj_data_contrato
        )
        
        db.session.add(novo_usuario)
        db.session.flush()  # Gera o ID sem fazer commit
        
        # Criar automaticamente Termo de Entrega e Responsabilidade
        if tipo_contrato == 'CLT':
            # Para CLT, usar dados da empresa
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
        else:  # PJ
            # Para PJ, usar dados do contrato PJ
            termo = TermoEntrega(
                id_usuario=novo_usuario.id,
                nome_colaborador=username,
                pj_contratante=pj_contratante,
                pj_contratante_cnpj=pj_contratante_cnpj,
                pj_contratante_endereco=pj_contratante_endereco,
                pj_contratada=pj_contratada,
                pj_contratada_cnpj=pj_contratada_cnpj,
                pj_data_contrato=pj_data_contrato
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
        tipo_contrato = request.form.get('tipo_contrato', usuario.tipo_contrato).strip().upper()
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
        # Campos PJ
        pj_contratante = request.form.get('pj_contratante', usuario.pj_contratante).strip()
        pj_contratante_cnpj = request.form.get('pj_contratante_cnpj', usuario.pj_contratante_cnpj).strip()
        pj_contratante_endereco = request.form.get('pj_contratante_endereco', usuario.pj_contratante_endereco).strip()
        pj_contratada = request.form.get('pj_contratada', usuario.pj_contratada).strip()
        pj_contratada_cnpj = request.form.get('pj_contratada_cnpj', usuario.pj_contratada_cnpj).strip()
        pj_data_contrato_str = request.form.get('pj_data_contrato', '')
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

        # Converter data do contrato PJ
        pj_data_contrato = usuario.pj_data_contrato
        if pj_data_contrato_str:
            try:
                from datetime import datetime
                pj_data_contrato = datetime.strptime(pj_data_contrato_str, '%Y-%m-%d').date()
            except:
                flash('Erro ao processar a data do contrato PJ.', 'error')
                return redirect(url_for('admin.editar_usuario', user_id=user_id))
        
        if role not in ['admin', 'usuario']:
            flash('Role inválido. Escolha entre admin ou usuario.', 'error')
            return redirect(url_for('admin.editar_usuario', user_id=user_id))

        if tipo_contrato not in ['CLT', 'PJ']:
            flash('Tipo de contrato inválido. Escolha entre CLT ou PJ.', 'error')
            return redirect(url_for('admin.editar_usuario', user_id=user_id))
        
        usuario.role = role
        usuario.tipo_contrato = tipo_contrato
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
        # Atualizar campos PJ
        usuario.pj_contratante = pj_contratante
        usuario.pj_contratante_cnpj = pj_contratante_cnpj
        usuario.pj_contratante_endereco = pj_contratante_endereco
        usuario.pj_contratada = pj_contratada
        usuario.pj_contratada_cnpj = pj_contratada_cnpj
        usuario.pj_data_contrato = pj_data_contrato
        usuario.ativo = ativo
        
        db.session.commit()
        
        registrar_evento(
            tipo_evento='usuario_editado',
            descricao=f'Usuário "{usuario.username}" editado - role: "{role}", tipo: "{tipo_contrato}", ativo: {ativo}',
            usuario_responsavel=current_user.username
        )
        
        flash(f'Usuário "{usuario.username}" atualizado com sucesso.', 'success')
        return redirect(url_for('admin.listar_usuarios'))
    
    return render_template('admin/user_form.html', mode='edit', usuario=usuario)


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
    page = request.args.get('page', 1, type=int)
    per_page = 10
    q = request.args.get('q', '').strip()
    tipo = request.args.get('tipo', '').strip().upper()

    usuarios_page = _listar_usuarios_paginados(page=page, per_page=per_page, q=q, tipo=tipo)
    return render_template('admin/usuarios.html', usuarios=usuarios_page, q=q, tipo=tipo)


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
    """Listar itens recebidos de um usuário e equipamentos do Termo"""
    usuario = User.query.get_or_404(user_id)
    
    # Carregar equipamentos do termo
    termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()
    equipamentos_termo = []
    if termo and termo.equipamentos:
        equipamentos_termo = json.loads(termo.equipamentos) if isinstance(termo.equipamentos, str) else termo.equipamentos
    
    # Carregar itens recebidos
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
        'equipamentos_termo': equipamentos_termo,
        'itens_entrada': [item.to_dict() for item in itens_entrada],
        'itens_posteriormente': [item.to_dict() for item in itens_posteriormente]
    })


@admin_bp.route('/usuarios/<int:user_id>/itens-recebidos/relatorio', methods=['GET'])
def gerar_relatorio_itens_usuario(user_id):
    """Gerar relatório em PDF com os itens recebidos do usuário"""
    usuario = User.query.get_or_404(user_id)

    itens_entrada = ItemRecebido.query.filter_by(
        id_usuario=user_id,
        tipo_recebimento='entrada'
    ).order_by(ItemRecebido.data_criacao.asc()).all()

    itens_posteriormente = ItemRecebido.query.filter_by(
        id_usuario=user_id,
        tipo_recebimento='posteriormente'
    ).order_by(ItemRecebido.data_criacao.asc()).all()

    try:
        from io import BytesIO
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.pdfgen import canvas
    except Exception:
        return jsonify({'success': False, 'message': 'Dependência reportlab não instalada. Rode: pip install reportlab'}), 500

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 18 * mm
    right = width - 18 * mm
    top = height - 18 * mm
    y = top

    def ensure_space(current_y, needed_height):
        if current_y - needed_height < 28 * mm:
            pdf.showPage()
            return top
        return current_y

    def draw_wrapped_text(text, x, current_y, max_width, font_name='Times-Roman', font_size=10, leading=13):
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
            pdf.drawString(x, current_y, line)
            current_y -= leading
        return current_y

    def draw_section_title(title, current_y):
        current_y = ensure_space(current_y, 16)
        pdf.setFont('Times-Bold', 11)
        pdf.drawString(left, current_y, title)
        return current_y - 12

    def draw_items_table(current_y, itens):
        if not itens:
            current_y = ensure_space(current_y, 12)
            pdf.setFont('Times-Roman', 10)
            pdf.drawString(left, current_y, 'Nenhum item nesta categoria.')
            return current_y - 14

        # Preparar dados da tabela
        table_data = [['Item', 'Data e Hora']]
        for item in itens:
            table_data.append([
                item.descricao_item,
                item.data_criacao.strftime('%d/%m/%Y %H:%M:%S') if item.data_criacao else ''
            ])

        # Dimensões das colunas
        col_widths = [100 * mm, 50 * mm]
        row_height = 14
        header_height = 16
        
        # Calcular altura total da tabela
        total_height = header_height + (len(table_data) - 1) * row_height
        current_y = ensure_space(current_y, total_height + 4)
        
        # Desenhar cabeçalho
        pdf.setFont('Times-Bold', 9)
        pdf.setFillColorRGB(0.94, 0.94, 0.94)  # Cor cinza claro
        header_y = current_y
        
        # Desenhar fundo do cabeçalho
        pdf.rect(left, header_y - header_height, sum(col_widths), header_height, fill=1, stroke=1)
        
        # Desenhar textos do cabeçalho
        pdf.setFillColorRGB(0, 0, 0)
        col_x = left
        for i, header in enumerate(table_data[0]):
            pdf.drawString(col_x + 2, header_y - 12, header)
            col_x += col_widths[i]
        
        # Desenhar linhas de dados
        pdf.setFont('Times-Roman', 9)
        data_y = header_y - header_height
        
        for row_idx, row in enumerate(table_data[1:]):
            col_x = left
            for col_idx, cell in enumerate(row):
                # Desenhar célula
                pdf.rect(col_x, data_y - row_height, col_widths[col_idx], row_height, fill=0, stroke=1)
                # Desenhar texto
                pdf.drawString(col_x + 2, data_y - 10, str(cell))
                col_x += col_widths[col_idx]
            
            data_y -= row_height
        
        return data_y - 6

    pdf.setTitle('Itens do Usuário')
    pdf.setFont('Times-Bold', 14)
    pdf.drawCentredString(width / 2, y, 'ITENS DO USUÁRIO')
    y -= 18

    cargo = getattr(usuario, 'cargo', '') or getattr(usuario, 'cargo_funcao', '') or ''
    cpf_cnpj = getattr(usuario, 'cpf', '') or getattr(usuario, 'cnpj', '') or ''
    data_admissao = usuario.data_admissao.strftime('%d/%m/%Y') if getattr(usuario, 'data_admissao', None) else ''

    campos = [
        ('Nome', usuario.username or ''),
        ('CPF/CNPJ', cpf_cnpj),
        ('Cargo/Função', cargo),
        ('Data de Admissão', data_admissao),
    ]

    pdf.setFont('Times-Roman', 10)
    for label, value in campos:
        y = ensure_space(y, 13)
        pdf.drawString(left, y, f'{label}:')
        pdf.line(left + 35 * mm, y - 1.5, right, y - 1.5)
        if value:
            pdf.drawString(left + 37 * mm, y + 0.5, str(value))
        y -= 13

    y -= 6
    y = draw_section_title('Itens Recebidos na Entrada', y)
    y = draw_items_table(y, itens_entrada)

    y = draw_section_title('Itens Recebidos Posteriormente', y)
    y = draw_items_table(y, itens_posteriormente)

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'itens_usuario_{usuario.id}.pdf'
    )


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
    termo_documento = DocumentoUsuario.query.filter_by(
        id_usuario=user_id,
        nome_documento='Termo de Entrega'
    ).first()
    tem_termo_gerado = termo_documento is not None

    # If termo doesn't exist, return an empty termo structure (modal will allow creating/updating)
    if not termo:
        termo_data = {
            'id': None,
            'id_usuario': usuario.id,
            'usuario': usuario.username,
            'tipo_contrato': usuario.tipo_contrato or 'CLT',
            'empresa': usuario.empresa or '',
            'cnpj': usuario.cnpj or '',
            'endereco': usuario.endereco or '',
            'nome_colaborador': usuario.username,
            'cargo_funcao': usuario.cargo or '',
            'cpf_cnpj': usuario.cpf or '',
            'departamento': usuario.departamento or '',
            'local_trabalho': usuario.local_trabalho or '',
            'data_admissao': usuario.data_admissao.strftime("%Y-%m-%d") if usuario.data_admissao else None,
            'pj_contratante': usuario.pj_contratante or '',
            'pj_contratante_cnpj': usuario.pj_contratante_cnpj or '',
            'pj_contratante_endereco': usuario.pj_contratante_endereco or '',
            'pj_contratada': usuario.pj_contratada or '',
            'pj_contratada_cnpj': usuario.pj_contratada_cnpj or '',
            'pj_data_contrato': usuario.pj_data_contrato.strftime("%Y-%m-%d") if usuario.pj_data_contrato else None,
            'equipamentos': [],
            'data_criacao': None,
            'data_atualizacao': None,
            'assinado': False,
            'data_assinatura': None,
            'observacoes': '',
            'tem_termo_gerado': tem_termo_gerado
        }

        return jsonify({
            'success': True,
            'termo': termo_data
        })

    termo_data = termo.to_dict()
    # Campo de input type="date" precisa de formato YYYY-MM-DD.
    termo_data['data_admissao'] = termo.data_admissao.strftime("%Y-%m-%d") if termo.data_admissao else ''
    termo_data['tipo_contrato'] = usuario.tipo_contrato or termo_data.get('tipo_contrato') or 'CLT'
    termo_data['pj_contratante'] = termo.pj_contratante or usuario.pj_contratante or ''
    termo_data['pj_contratante_cnpj'] = termo.pj_contratante_cnpj or usuario.pj_contratante_cnpj or ''
    termo_data['pj_contratante_endereco'] = termo.pj_contratante_endereco or usuario.pj_contratante_endereco or ''
    termo_data['pj_contratada'] = termo.pj_contratada or usuario.pj_contratada or ''
    termo_data['pj_contratada_cnpj'] = termo.pj_contratada_cnpj or usuario.pj_contratada_cnpj or ''
    termo_data['pj_data_contrato'] = (
        termo.pj_data_contrato.strftime("%Y-%m-%d") if termo.pj_data_contrato else
        (usuario.pj_data_contrato.strftime("%Y-%m-%d") if usuario.pj_data_contrato else '')
    )
    termo_data['tem_termo_gerado'] = tem_termo_gerado

    return jsonify({
        'success': True,
        'termo': termo_data
    })


@admin_bp.route('/usuarios/<int:user_id>/termo-entrega/atualizar', methods=['POST'])
def atualizar_termo_entrega(user_id):
    """Atualizar informações do Termo de Entrega (apenas se não foi gerado ainda)"""
    usuario = User.query.get_or_404(user_id)
    termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()

    # If termo doesn't exist, create it
    if not termo:
        if usuario.tipo_contrato == 'PJ':
            termo = TermoEntrega(
                id_usuario=user_id,
                nome_colaborador=usuario.username,
                pj_contratante=usuario.pj_contratante or '',
                pj_contratante_cnpj=usuario.pj_contratante_cnpj or '',
                pj_contratante_endereco=usuario.pj_contratante_endereco or '',
                pj_contratada=usuario.pj_contratada or '',
                pj_contratada_cnpj=usuario.pj_contratada_cnpj or '',
                pj_data_contrato=usuario.pj_data_contrato
            )
        else:
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
    
    # Note: allow updating termo fields even if a Termo document exists.
    termo_documento = DocumentoUsuario.query.filter_by(
        id_usuario=user_id,
        nome_documento='Termo de Entrega'
    ).first()

    # Atualizar informações do termo
    termo.empresa = request.form.get('empresa', termo.empresa or '').strip()
    termo.cnpj = request.form.get('cnpj', termo.cnpj or '').strip()
    termo.endereco = request.form.get('endereco', termo.endereco or '').strip()
    termo.cargo_funcao = request.form.get('cargo_funcao', termo.cargo_funcao or '').strip()
    termo.cpf_cnpj = request.form.get('cpf_cnpj', termo.cpf_cnpj or '').strip()
    termo.departamento = request.form.get('departamento', termo.departamento or '').strip()
    termo.local_trabalho = request.form.get('local_trabalho', termo.local_trabalho or '').strip()
    
    # Atualizar campos PJ no Termo
    pj_contratante = request.form.get('pj_contratante', '').strip()
    pj_contratante_cnpj = request.form.get('pj_contratante_cnpj', '').strip()
    pj_contratante_endereco = request.form.get('pj_contratante_endereco', '').strip()
    pj_contratada = request.form.get('pj_contratada', '').strip()
    pj_contratada_cnpj = request.form.get('pj_contratada_cnpj', '').strip()
    
    if pj_contratante:
        termo.pj_contratante = pj_contratante
    if pj_contratante_cnpj:
        termo.pj_contratante_cnpj = pj_contratante_cnpj
    if pj_contratante_endereco:
        termo.pj_contratante_endereco = pj_contratante_endereco
    if pj_contratada:
        termo.pj_contratada = pj_contratada
    if pj_contratada_cnpj:
        termo.pj_contratada_cnpj = pj_contratada_cnpj

    data_admissao_str = request.form.get('data_admissao', '').strip()
    if data_admissao_str:
        try:
            termo.data_admissao = datetime.strptime(data_admissao_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Data de admissão inválida. Use o formato AAAA-MM-DD.'
            }), 400
    else:
        termo.data_admissao = None
    
    pj_data_contrato_str = request.form.get('pj_data_contrato', '').strip()
    if pj_data_contrato_str:
        try:
            termo.pj_data_contrato = datetime.strptime(pj_data_contrato_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    observacoes = request.form.get('observacoes', '').strip()
    termo.observacoes = observacoes

    # Atualizar campos PJ no usuário (se fornecidos pelo modal)
    if pj_contratante:
        usuario.pj_contratante = pj_contratante
    if pj_contratante_cnpj:
        usuario.pj_contratante_cnpj = pj_contratante_cnpj
    if pj_contratante_endereco:
        usuario.pj_contratante_endereco = pj_contratante_endereco
    if pj_contratada:
        usuario.pj_contratada = pj_contratada
    if pj_contratada_cnpj:
        usuario.pj_contratada_cnpj = pj_contratada_cnpj
    if pj_data_contrato_str:
        try:
            usuario.pj_data_contrato = datetime.strptime(pj_data_contrato_str, '%Y-%m-%d').date()
        except Exception:
            pass

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
    """Adicionar equipamento ao Termo de Entrega (ou criar aditivo se termo já foi assinado)"""
    usuario = User.query.get_or_404(user_id)
    termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()
    termo_documento = DocumentoUsuario.query.filter_by(
        id_usuario=user_id,
        nome_documento='Termo de Entrega'
    ).first()

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
    estado = request.form.get('estado', 'Novo').strip()
    service_tag = request.form.get('service_tag', '').strip()

    if not descricao:
        return jsonify({
            'success': False,
            'message': 'Descrição do equipamento é obrigatória.'
        }), 400

    # Carregar equipamentos existentes
    equipamentos = json.loads(termo.equipamentos) if termo.equipamentos else []
    ids_existentes = [eq.get('id') for eq in equipamentos if isinstance(eq, dict) and isinstance(eq.get('id'), int)]
    proximo_id = max(ids_existentes, default=0) + 1

    # Adicionar novo equipamento
    novo_equipamento = {
        'id': proximo_id,
        'descricao': descricao,
        'marca': marca,
        'modelo': modelo,
        'estado': estado,
        'service_tag': service_tag,
        'data_entrega': datetime.now(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y")
    }

    # Marcar o item como termo ou aditivo para a geração correta do PDF
    novo_equipamento['tipo_documento'] = 'aditivo' if termo_documento else 'termo'
    novo_equipamento['data_registro'] = datetime.now(timezone(timedelta(hours=-3))).isoformat()

    # Salvar fotos (se houver) em static/uploads/termos
    saved_fotos = []
    try:
        upload_folder = os.path.join(current_app.static_folder, 'uploads', 'termos')
        os.makedirs(upload_folder, exist_ok=True)
        arquivos = request.files.getlist('fotos') if 'fotos' in request.files else []
        titulos_fotos = request.form.getlist('fotos_titulos')

        for indice, arquivo in enumerate(arquivos):
            if arquivo and arquivo.filename:
                filename = secure_filename(arquivo.filename)
                unique_name = f"{int(datetime.now(timezone(timedelta(hours=-3))).timestamp())}_{uuid4().hex}_{filename}"
                arquivo.save(os.path.join(upload_folder, unique_name))
                titulo_foto = titulos_fotos[indice].strip() if indice < len(titulos_fotos) and titulos_fotos[indice] else f'Foto {indice + 1}'
                saved_fotos.append({
                    'arquivo': unique_name,
                    'titulo': titulo_foto,
                })
    except Exception as e:
        # não bloquear a criação do equipamento por erro no upload; registrar evento
        registrar_evento(
            tipo_evento='erro_upload_foto_termo',
            descricao=f'Erro ao salvar foto do termo para usuário "{usuario.username}": {str(e)}',
            usuario_responsavel=current_user.username
        )

    if saved_fotos:
        novo_equipamento['fotos'] = saved_fotos

    equipamentos.append(novo_equipamento)

    # Salvar equipamentos atualizados
    termo.equipamentos = json.dumps(equipamentos)
    db.session.commit()

    # Se termo já foi gerado, avisar que criará aditivo na próxima geração
    criar_aditivo = termo_documento is not None

    registrar_evento(
        tipo_evento='equipamento_adicionado_termo',
        descricao=f'Equipamento "{descricao}" adicionado ao Termo de Entrega de "{usuario.username}"' + (' (será em ADITIVO)' if criar_aditivo else ''),
        usuario_responsavel=current_user.username
    )

    return jsonify({
        'success': True,
        'message': 'Equipamento adicionado com sucesso!' + (' Um ADITIVO será criado na próxima geração.' if criar_aditivo else ''),
        'equipamento': novo_equipamento,
        'criar_aditivo': criar_aditivo
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
    """Rota descontinuada: a geração agora depende apenas do documento salvo."""
    usuario = User.query.get_or_404(user_id)
    termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()

    return jsonify({
        'success': False,
        'message': 'A assinatura foi removida do fluxo. Use a geração do Termo ou do Aditivo conforme o documento salvo.'
    })


@admin_bp.route('/usuarios/<int:user_id>/termo-entrega/exportar', methods=['POST'])
def exportar_termo_pdf(user_id):
    """Gerar arquivo .pdf do Termo preenchido e salvar em uploads/documentos"""
    try:
        import os
        from app.services.termo_service import TermoService
        
        # Aceitar parâmetro aditivo do POST
        dados_json = request.get_json(silent=True) or {}
        forcar_aditivo = dados_json.get('aditivo', False)
        
        usuario = User.query.get_or_404(user_id)
        termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()

        if not termo:
            return jsonify({'success': False, 'message': 'Termo não encontrado para este usuário'}), 404

        try:
            TermoService
        except Exception:
            return jsonify({'success': False, 'message': 'Serviço de Termo não disponível'}), 500

        pasta = os.path.abspath(os.path.join(current_app.root_path, '..', 'static', 'uploads', 'documentos'))
        os.makedirs(pasta, exist_ok=True)

        termo_documento = DocumentoUsuario.query.filter_by(
            id_usuario=user_id,
            nome_documento='Termo de Entrega'
        ).first()

        equipamentos = []
        if termo.equipamentos:
            try:
                equipamentos = json.loads(termo.equipamentos) if isinstance(termo.equipamentos, str) else termo.equipamentos
            except Exception:
                equipamentos = []

        tem_tipo_documento = any('tipo_documento' in eq for eq in equipamentos)
        tem_equipamento_aditivo = any(eq.get('tipo_documento') == 'aditivo' for eq in equipamentos)

        # Se forcar_aditivo é True, sempre criar aditivo, caso contrário usar lógica de detecção
        eh_aditivo = forcar_aditivo or tem_equipamento_aditivo or (termo_documento is not None and not tem_tipo_documento)
        numero_aditivo = 0

        if eh_aditivo:
            aditivos_existentes = DocumentoUsuario.query.filter(
                DocumentoUsuario.id_usuario == user_id,
                DocumentoUsuario.nome_documento.like('Aditivo ao Termo%')
            ).count()
            numero_aditivo = aditivos_existentes + 1
            nome_arquivo = f'termo_{usuario.id}_aditivo_{numero_aditivo}.pdf'
            nome_doc = f'Aditivo ao Termo de Entrega #{numero_aditivo}'
            descricao_doc = f'Aditivo #{numero_aditivo} ao Termo de Entrega'
        else:
            nome_arquivo = f'termo_{usuario.id}.pdf'
            nome_doc = 'Termo de Entrega'
            descricao_doc = 'Termo de Entrega e Responsabilidade'

        caminho = os.path.join(pasta, nome_arquivo)

        # Gerar PDF usando TermoService (passa flag se é aditivo)
        TermoService.gerar_pdf(user_id, caminho, eh_aditivo)

        tamanho = os.path.getsize(caminho)
        usuario_enviador = getattr(current_user, 'username', None) or 'sistema'

        # If regenerating the base Termo (not an aditivo) and a Termo document already exists,
        # overwrite the existing document record instead of creating a duplicate.
        if not eh_aditivo and termo_documento:
            termo_documento.arquivo = nome_arquivo
            termo_documento.tipo_arquivo = 'pdf'
            termo_documento.tamanho_arquivo = tamanho
            termo_documento.usuario_enviador = usuario_enviador
            termo_documento.descricao = descricao_doc
            db.session.commit()
            novo_doc = termo_documento
        else:
            novo_doc = DocumentoUsuario(
                id_usuario=usuario.id,
                nome_documento=nome_doc,
                arquivo=nome_arquivo,
                tipo_arquivo='pdf',
                tamanho_arquivo=tamanho,
                usuario_enviador=usuario_enviador,
                descricao=descricao_doc
            )
            db.session.add(novo_doc)
            db.session.commit()

        if eh_aditivo:
            equipamentos_aditivo = [
                eq for eq in equipamentos
                if eq.get('tipo_documento') == 'aditivo'
            ]
            # Compatibilidade com registros antigos: se ainda não existir marcação,
            # mantém o comportamento anterior apenas quando não houver itens marcados.
            if not equipamentos_aditivo and not any('tipo_documento' in eq for eq in equipamentos):
                equipamentos_aditivo = equipamentos
            equipamentos = equipamentos_aditivo

        itens_existentes = ItemRecebido.query.filter_by(id_usuario=user_id).count()
        tipo_recebimento = 'posteriormente' if itens_existentes > 0 else 'entrada'
        
        for eq in equipamentos:
            descricao = f"{eq.get('descricao', '')} ({eq.get('marca', '')}/{eq.get('modelo', '')})"
            item_existe = ItemRecebido.query.filter_by(
                id_usuario=user_id,
                descricao_item=descricao
            ).first()

            if not item_existe:
                novo_item = ItemRecebido(
                    id_usuario=user_id,
                    descricao_item=descricao,
                    tipo_recebimento=tipo_recebimento,
                    usuario_responsavel=usuario_enviador
                )
                db.session.add(novo_item)

        db.session.commit()

        registrar_evento(
            tipo_evento='termo_entrega_gerado' if not eh_aditivo else 'aditivo_termo_gerado',
            descricao=f'{"Termo de Entrega" if not eh_aditivo else f"Aditivo #{numero_aditivo}"} do usuário "{usuario.username}" foi gerado',
            usuario_responsavel=current_user.username
        )

        mensagem = f'{"Termo" if not eh_aditivo else "Aditivo"} exportado e salvo com sucesso.'
        return jsonify({'success': True, 'message': mensagem, 'documento_id': novo_doc.id_documento})
        
    except Exception as e:
        import traceback
        erro_details = traceback.format_exc()
        registrar_evento(
            tipo_evento='erro_geracao_pdf',
            descricao=f'Erro ao gerar PDF para usuário {user_id}: {str(e)}',
            usuario_responsavel=current_user.username if current_user.is_authenticated else 'sistema'
        )
        return jsonify({'success': False, 'message': f'Erro ao gerar PDF: {str(e)}'}), 500
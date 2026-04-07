from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from database import create_app, db, DATABASE_URL
from estoque_db import EstoqueDB
from models import Produto, Movimentacao, User, Chamada, Historico
import os

# Criar aplicacao Flask
app, db = create_app()

# Exibir informacoes de configuracao
print("\n" + "="*60)
print("Sistema de Estoque - Inicializando...")
print("="*60)
if "mysql" in DATABASE_URL:
    db_type = "MySQL"
elif "sqlite" in DATABASE_URL:
    db_type = "SQLite"
else:
    db_type = "Desconhecido"
print(f"Banco de dados: {db_type}")
if db_type == "SQLite":
    raise SystemExit(
        "SQLite não é suportado neste modo.\n"
        "Defina DATABASE_URL no .env para MySQL:\n"
        "DATABASE_URL=mysql+pymysql://estoque_user:12345@localhost:3306/estoque_db"
    )
print("="*60 + "\n")

# Garantir que a coluna de status exista (compatibilidade com banco já em uso)
with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE chamadas ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'nova'"))
        db.session.commit()
    except Exception:
        # Coluna provavelmente já existe, continuar normalmente
        db.session.rollback()

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faca login para acessar esta pagina.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Instância global do estoque (será inicializada depois)
estoque = None

# ============================================================================
# FUNÇÃO AUXILIAR - REGISTRO DE HISTÓRICO
# ============================================================================

def registrar_evento(tipo_evento, descricao, usuario_responsavel=None, detalhes=None):
    """Registra um evento no histórico do sistema"""
    try:
        if usuario_responsavel is None and current_user.is_authenticated:
            usuario_responsavel = current_user.username
        
        evento = Historico(
            tipo_evento=tipo_evento,
            descricao=descricao,
            usuario_responsavel=usuario_responsavel,
            detalhes=detalhes
        )
        db.session.add(evento)
        db.session.commit()
    except Exception as e:
        print(f"Erro ao registrar evento no histórico: {e}")

# ============================================================================
# ROTAS - AUTENTICAÇÃO
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Nome de usuário ou senha incorretos.', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    session.pop('perfil_verified', None)
    session.pop('perfil_previous', None)
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin():
    """Página de administração de usuários"""
    if not current_user.is_admin:
        return redirect(url_for('chamadas'))
    return render_template('admin.html')

@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    """Tela de perfil com reautenticação antes de permitir mudança de senha."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username != current_user.username or not check_password_hash(current_user.password, password):
            flash('Erro: login diferente ou senha inválida.', 'error')
            destino = session.pop('perfil_previous', None) or url_for('index')
            return redirect(destino)

        session['perfil_verified'] = True
        return redirect(url_for('perfil'))

    if session.get('perfil_verified'):
        return render_template('profile.html', usuario=current_user.username)

    if 'perfil_previous' not in session:
        anterior = request.referrer
        if anterior and not anterior.endswith(url_for('perfil')):
            session['perfil_previous'] = anterior
        else:
            session['perfil_previous'] = url_for('index')

    return render_template('profile_auth.html', usuario=current_user.username)

@app.route('/perfil/password', methods=['POST'])
@login_required
def perfil_password():
    if not session.get('perfil_verified'):
        flash('Por favor, reautentique para acessar o perfil.', 'error')
        return redirect(url_for('perfil'))

    login_name = request.form.get('login_name', '').strip()
    senha_atual = request.form.get('senha_atual', '').strip()
    nova_senha = request.form.get('nova_senha', '').strip()
    confirm_nova_senha = request.form.get('confirm_nova_senha', '').strip()

    if login_name != current_user.username:
        flash('O nome de login informado deve ser o seu próprio login.', 'error')
        return redirect(url_for('perfil'))

    if not senha_atual or not nova_senha or not confirm_nova_senha:
        flash('Todos os campos são obrigatórios.', 'error')
        return redirect(url_for('perfil'))

    if not check_password_hash(current_user.password, senha_atual):
        flash('Senha atual incorreta.', 'error')
        return redirect(url_for('perfil'))

    if nova_senha != confirm_nova_senha:
        flash('A nova senha deve ser digitada duas vezes de forma idêntica.', 'error')
        return redirect(url_for('perfil'))

    if senha_atual == nova_senha:
        flash('A nova senha deve ser diferente da senha atual.', 'error')
        return redirect(url_for('perfil'))

    current_user.password = generate_password_hash(nova_senha, method='pbkdf2:sha256')
    db.session.commit()

    registrar_evento(
        tipo_evento='senha_alterada',
        descricao=f'Senha alterada pelo usuário "{current_user.username}" via perfil',
        usuario_responsavel=current_user.username
    )

    flash('Senha atualizada com sucesso.', 'success')
    return redirect(url_for('perfil'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        mensagem = request.form.get('mensagem', '').strip()

        if not username:
            flash('Informe o nome de usuário para solicitar a redefinição.', 'error')
            return redirect(url_for('forgot_password'))

        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('forgot_password'))

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
        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

# ============================================================================
# ROTAS - API DE USUÁRIOS
# ============================================================================

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """Retorna lista de usuários (apenas para admins)"""
    if not current_user.is_admin:
        return jsonify({'erro': 'Acesso negado'}), 403
    
    users = User.query.all()
    resultado = []
    for user in users:
        resultado.append({
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'data_criacao': user.data_criacao.strftime("%d/%m/%Y %H:%M:%S") if user.data_criacao else None
        })
    return jsonify(resultado)

@app.route('/api/users', methods=['POST'])
@login_required
def criar_user():
    """Cria um novo usuário (apenas para admins)"""
    if not current_user.is_admin:
        return jsonify({'erro': 'Acesso negado'}), 403
    
    dados = request.get_json()
    username = dados.get('username')
    password = dados.get('password')
    role = dados.get('role', 'user')
    
    if not username or not password:
        return jsonify({'erro': 'Username e password são obrigatórios'}), 400
    
    if role not in ['user', 'admin']:
        return jsonify({'erro': 'Role deve ser "user" ou "admin"'}), 400
    
    # Verificar se username já existe
    if User.query.filter_by(username=username).first():
        return jsonify({'erro': 'Username já existe'}), 400
    
    novo_user = User(username=username, password=generate_password_hash(password, method='pbkdf2:sha256'), role=role)
    db.session.add(novo_user)
    db.session.commit()
    
    registrar_evento(
        tipo_evento='usuario_criado',
        descricao=f'Usuário "{username}" criado com papel: {role}'
    )
    
    return jsonify({'mensagem': 'Usuário criado com sucesso'}), 201

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def deletar_user(user_id):
    """Remove um usuário (apenas para admins)"""
    if not current_user.is_admin:
        return jsonify({'erro': 'Acesso negado'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    # Não permitir deletar o próprio usuário
    if user.id == current_user.id:
        return jsonify({'erro': 'Não é possível deletar o próprio usuário'}), 400
    
    username_deletado = user.username
    db.session.delete(user)
    db.session.commit()
    
    registrar_evento(
        tipo_evento='usuario_deletado',
        descricao=f'Usuário "{username_deletado}" foi removido'
    )
    
    return jsonify({'mensagem': 'Usuário removido com sucesso'})

@app.route('/api/users/me/password', methods=['PUT'])
@login_required
def alterar_senha_propria():
    """Permite que o usuário autenticado altere sua própria senha."""
    dados = request.get_json() or {}
    senha_atual = dados.get('senha_atual', '').strip()
    senha_atual_rep = dados.get('senha_atual_rep', '').strip()
    nova_senha = dados.get('nova_senha', '').strip()
    confirm_nova_senha = dados.get('confirm_nova_senha', '').strip()

    if not senha_atual or not senha_atual_rep or not nova_senha or not confirm_nova_senha:
        return jsonify({'erro': 'Todos os campos de senha são obrigatórios'}), 400

    if senha_atual != senha_atual_rep:
        return jsonify({'erro': 'A senha atual deve ser digitada duas vezes de forma idêntica'}), 400

    if nova_senha != confirm_nova_senha:
        return jsonify({'erro': 'A nova senha deve ser digitada duas vezes de forma idêntica'}), 400

    if not check_password_hash(current_user.password, senha_atual):
        return jsonify({'erro': 'Senha atual incorreta'}), 400

    if senha_atual == nova_senha:
        return jsonify({'erro': 'A nova senha deve ser diferente da senha atual'}), 400

    current_user.password = generate_password_hash(nova_senha, method='pbkdf2:sha256')
    db.session.commit()

    registrar_evento(
        tipo_evento='senha_alterada',
        descricao=f'Senha alterada para usuário "{current_user.username}"',
        usuario_responsavel=current_user.username
    )

    return jsonify({'mensagem': 'Senha atualizada com sucesso'})

@app.route('/api/users/<int:user_id>/reset-password', methods=['PUT'])
@login_required
def resetar_senha_usuario(user_id):
    """Permite que um admin redefina a senha de outro usuário."""
    if not current_user.is_admin:
        return jsonify({'erro': 'Acesso negado'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'erro': 'Usuário não encontrado'}), 404

    dados = request.get_json() or {}
    nova_senha = dados.get('nova_senha', '').strip()
    confirm_nova_senha = dados.get('confirm_nova_senha', '').strip()

    if not nova_senha or not confirm_nova_senha:
        return jsonify({'erro': 'Nova senha é obrigatória'}), 400

    if nova_senha != confirm_nova_senha:
        return jsonify({'erro': 'A nova senha deve ser digitada duas vezes de forma idêntica'}), 400

    user.password = generate_password_hash(nova_senha, method='pbkdf2:sha256')
    db.session.commit()

    registrar_evento(
        tipo_evento='senha_resetada',
        descricao=f'Senha redefinida para usuário "{user.username}"',
        usuario_responsavel=current_user.username
    )

    return jsonify({'mensagem': f'Senha do usuário {user.username} redefinida com sucesso'})

@app.route('/api/users/<int:user_id>/request-password-reset', methods=['POST'])
@login_required
def solicitar_redefinicao_senha(user_id):
    """Cria um chamado de esqueci a senha para o usuário especificado."""
    if not current_user.is_admin:
        return jsonify({'erro': 'Acesso negado'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'erro': 'Usuário não encontrado'}), 404

    dados = request.get_json() or {}
    descricao_extra = dados.get('mensagem', '').strip()
    if descricao_extra:
        texto_chamada = f'Esqueci a senha - usuário "{user.username}": {descricao_extra}'
    else:
        texto_chamada = f'Esqueci a senha - usuário "{user.username}" solicita redefinição de senha.'

    chamada = Chamada(id_usuario=user.id, mensagem=texto_chamada)
    db.session.add(chamada)
    db.session.commit()

    registrar_evento(
        tipo_evento='senha_esquecida',
        descricao=f'Chamado de redefinição de senha para o usuário "{user.username}"',
        usuario_responsavel=current_user.username
    )

    return jsonify({'mensagem': 'Chamado de redefinição de senha criado com sucesso'}), 201

# ============================================================================
# ROTAS - CHAMADAS/NOTIFICAÇÕES
# ============================================================================

@app.route('/api/chamadas', methods=['POST'])
@login_required
def criar_chamada():
    """Cria uma nova chamada/notificação para admins"""
    if current_user.is_admin:
        return jsonify({'erro': 'Administradores não podem enviar chamadas'}), 400
    
    dados = request.get_json()
    tipo = dados.get('tipo', '').strip()
    subtipo = dados.get('subtipo', '').strip()
    mensagem = dados.get('mensagem', '').strip()
    
    if not tipo:
        return jsonify({'erro': 'Tipo de chamada é obrigatório'}), 400

    if tipo != 'Outros' and not subtipo:
        return jsonify({'erro': 'Subtipo é obrigatório para este tipo de chamada'}), 400

    if not mensagem:
        return jsonify({'erro': 'Mensagem é obrigatória'}), 400
    
    if tipo == 'Outros':
        mensagem_com_tipo = f'[{tipo}] {mensagem}'
    else:
        mensagem_com_tipo = f'[{tipo} - {subtipo}] {mensagem}'
    
    nova_chamada = Chamada(id_usuario=current_user.id, mensagem=mensagem_com_tipo)
    db.session.add(nova_chamada)
    db.session.commit()
    
    return jsonify({'mensagem': 'Chamada enviada com sucesso'}), 201

@app.route('/api/chamadas', methods=['GET'])
@login_required
def get_chamadas():
    """Retorna lista de chamadas."""
    limit = request.args.get('limit', type=int)
    if current_user.is_admin:
        query = Chamada.query.order_by(Chamada.data_criacao.desc())
    else:
        query = Chamada.query.filter_by(id_usuario=current_user.id).order_by(Chamada.data_criacao.desc())

    if limit and limit > 0:
        query = query.limit(limit)

    chamadas = query.all()
    resultado = [chamada.to_dict() for chamada in chamadas]
    
    return jsonify(resultado)

@app.route('/api/chamadas/<int:chamada_id>/ler', methods=['PUT'])
@login_required
def marcar_chamada_lida(chamada_id):
    """Marca uma chamada como lida (apenas para admins)"""
    if not current_user.is_admin:
        return jsonify({'erro': 'Acesso negado'}), 403
    
    chamada = Chamada.query.get(chamada_id)
    if not chamada:
        return jsonify({'erro': 'Chamada não encontrada'}), 404
    
    chamada.lida = True
    chamada.status = 'lida'
    db.session.commit()

    registrar_evento(
        tipo_evento='chamada_status',
        descricao=f'Chamada {chamada.id_chamada} marcada como Lida',
        usuario_responsavel=current_user.username,
        detalhes='status=lida'
    )
    
    return jsonify({'mensagem': 'Chamada marcada como lida'})

@app.route('/api/chamadas/<int:chamada_id>/status', methods=['PUT'])
@login_required
def atualizar_status_chamada(chamada_id):
    """Atualiza o status de uma chamada (apenas para admins)"""
    if not current_user.is_admin:
        return jsonify({'erro': 'Acesso negado'}), 403

    chamada = Chamada.query.get(chamada_id)
    if not chamada:
        return jsonify({'erro': 'Chamada não encontrada'}), 404

    dados = request.get_json() or {}
    novo_status = dados.get('status', '').strip().lower()

    estagios_validos = ['nova', 'lida', 'analise', 'execucao', 'concluida']
    if novo_status not in estagios_validos:
        return jsonify({'erro': 'Status inválido'}), 400

    # Validação de transições permitidas
    transicoes = {
        'nova': ['lida'],
        'lida': ['analise'],
        'analise': ['execucao'],
        'execucao': ['concluida'],
        'concluida': []
    }

    if novo_status == chamada.status:
        return jsonify({'mensagem': 'Status já está definido'}), 200

    if novo_status not in transicoes.get(chamada.status, []):
        return jsonify({'erro': f'Transição de status não permitida: {chamada.status} -> {novo_status}'}), 400

    chamada.status = novo_status
    chamada.lida = novo_status != 'nova'
    db.session.commit()

    registrar_evento(
        tipo_evento='chamada_status',
        descricao=f'Chamada {chamada.id_chamada} atualizada para {novo_status}',
        usuario_responsavel=current_user.username,
        detalhes=f'status={novo_status}'
    )

    return jsonify({'mensagem': f'Status atualizado para {novo_status}'})

@app.route('/api/chamadas/nao-lidas', methods=['GET'])
@login_required
def get_chamadas_nao_lidas():
    """Retorna quantidade de chamadas não lidas."""
    if current_user.is_admin:
        nao_lidas = Chamada.query.filter_by(lida=False).count()
    else:
        nao_lidas = Chamada.query.filter_by(id_usuario=current_user.id, lida=False).count()
    return jsonify({'nao_lidas': nao_lidas})

# ============================================================================
# ROTAS - HISTÓRICO/AUDITORIA
# ============================================================================

@app.route('/api/historico', methods=['GET'])
@login_required
def get_historico():
    """Retorna histórico de eventos do sistema (apenas para admins)"""
    if not current_user.is_admin:
        return jsonify({'erro': 'Acesso negado'}), 403
    
    limit = request.args.get('limit', 50, type=int)
    tipo_filtro = request.args.get('tipo')
    
    query = Historico.query.order_by(Historico.data_evento.desc())
    
    if tipo_filtro:
        query = query.filter_by(tipo_evento=tipo_filtro)
    
    eventos = query.limit(limit).all()
    resultado = [evento.to_dict() for evento in eventos]
    
    return jsonify(resultado)

@app.route('/api/historico/tipos', methods=['GET'])
@login_required
def get_tipos_historico():
    """Retorna lista de tipos de eventos disponíveis"""
    if not current_user.is_admin:
        return jsonify({'erro': 'Acesso negado'}), 403
    
    tipos = [
        'usuario_criado',
        'usuario_deletado',
        'produto_criado',
        'produto_deletado',
        'entrada_estoque',
        'saida_estoque'
    ]
    return jsonify({'tipos': tipos})

# ============================================================================
# ROTAS - PÁGINA PRINCIPAL
# ============================================================================

@app.route('/')
@login_required
def index():
    """Página principal do dashboard"""
    return render_template('index.html')


# ============================================================================
# ROTAS - API DE PRODUTOS
# ============================================================================

@app.route('/api/produtos', methods=['GET'])
@login_required
def get_produtos():
    """Retorna lista de todos os produtos"""
    try:
        produtos = estoque.listar_produtos()
        return jsonify([prod.to_dict() for prod in produtos])
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


def validar_dados_produto(dados, atualizar=False):
    erros = []

    if not dados:
        erros.append('JSON inválido ou vazio')
        return erros

    id_produto = dados.get('id') if not atualizar else None
    nome = dados.get('nome')
    categoria = dados.get('categoria')
    preco = dados.get('preco')
    quantidade = dados.get('quantidade')
    minimo = dados.get('minimo')

    if not atualizar:
        if not id_produto or not str(id_produto).strip():
            erros.append('ID do produto é obrigatório')

    if not nome or not str(nome).strip():
        erros.append('Nome é obrigatório')

    if not categoria or not str(categoria).strip():
        erros.append('Categoria é obrigatória')

    try:
        preco = float(preco)
        if preco < 0:
            erros.append('Preço não pode ser negativo')
    except Exception:
        erros.append('Preço inválido')

    try:
        quantidade = int(quantidade)
        if quantidade < 0:
            erros.append('Quantidade não pode ser negativa')
    except Exception:
        erros.append('Quantidade inválida')

    try:
        minimo = int(minimo)
        if minimo < 0:
            erros.append('Mínimo não pode ser negativo')
    except Exception:
        erros.append('Mínimo inválido')

    return erros


@app.route('/api/produtos/<id_produto>', methods=['GET'])
@login_required
def get_produto(id_produto):
    """Retorna um produto específico"""
    try:
        produto = estoque.buscar_produto(id_produto)
        if not produto:
            return jsonify({'erro': 'Produto não encontrado'}), 404

        return jsonify(produto.to_dict())
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/produtos', methods=['POST'])
@login_required
def criar_produto():
    """Cria um novo produto"""
    try:
        dados = request.get_json()
        erros = validar_dados_produto(dados, atualizar=False)
        if erros:
            return jsonify({'erro': ' | '.join(erros)}), 400

        sucesso = estoque.adicionar_produto(
            id_produto=str(dados['id']).strip(),
            nome=str(dados['nome']).strip(),
            categoria=str(dados['categoria']).strip(),
            preco=float(dados['preco']),
            quantidade=int(dados['quantidade']),
            minimo=int(dados['minimo']),
            localizacao=str(dados.get('localizacao', '')).strip()
        )

        if sucesso:
            registrar_evento(
                tipo_evento='produto_criado',
                descricao=f'Produto "{dados["nome"]}" (ID: {dados["id"]}) foi criado com sucesso'
            )
            return jsonify({'mensagem': 'Produto criado com sucesso'}), 201
        else:
            return jsonify({'erro': 'Falha ao criar produto'}), 400

    except Exception as e:
        return jsonify({'erro': str(e)}), 400


@app.route('/api/produtos/<id_produto>', methods=['PUT'])
@login_required
def atualizar_produto(id_produto):
    """Atualiza um produto"""
    dados = request.get_json()
    produto = estoque.buscar_produto(id_produto)
    
    if not produto:
        return jsonify({'erro': 'Produto não encontrado'}), 404

    erros = validar_dados_produto(dados, atualizar=True)
    if erros:
        return jsonify({'erro': ' | '.join(erros)}), 400

    try:
        dados_update = {
            'nome': str(dados['nome']).strip(),
            'categoria': str(dados['categoria']).strip(),
            'preco': float(dados['preco']),
            'quantidade': int(dados['quantidade']),
            'minimo': int(dados['minimo']),
            'localizacao': str(dados.get('localizacao', '')).strip()
        }

        sucesso = estoque.atualizar_produto(id_produto, **dados_update)
        if not sucesso:
            return jsonify({'erro': 'Falha ao atualizar produto'}), 400

        produto_atualizado = estoque.buscar_produto(id_produto)
        return jsonify({
            'mensagem': 'Produto atualizado com sucesso',
            'produto': produto_atualizado.to_dict()
        })

    except Exception as e:
        return jsonify({'erro': str(e)}), 400


@app.route('/api/produtos/<id_produto>', methods=['DELETE'])
@login_required
def deletar_produto(id_produto):
    """Delete um produto"""
    try:
        produto = estoque.buscar_produto(id_produto)
        nome_produto = produto.nome if produto else id_produto
        
        sucesso = estoque.remover_produto(id_produto)

        if sucesso:
            registrar_evento(
                tipo_evento='produto_deletado',
                descricao=f'Produto "{nome_produto}" (ID: {id_produto}) foi removido'
            )
            return jsonify({'mensagem': 'Produto removido com sucesso'})
        else:
            return jsonify({'erro': 'Produto não encontrado'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


# ============================================================================
# ROTAS - MOVIMENTAÇÕES DE ESTOQUE
# ============================================================================

@app.route('/api/entrada', methods=['POST'])
@login_required
def entrada_estoque():
    """Registra entrada de produtos"""
    try:
        dados = request.get_json()

        sucesso = estoque.entrada_estoque(
            id_produto=dados['id'],
            quantidade=int(dados['quantidade']),
            motivo=dados.get('motivo', ''),
            usuario=dados.get('usuario', '')
        )

        if sucesso:
            registrar_evento(
                tipo_evento='entrada_estoque',
                descricao=f'Entrada de {dados["quantidade"]} unidades do produto ID: {dados["id"]} - Motivo: {dados.get("motivo", "Não informado")}'
            )
            return jsonify({'mensagem': 'Entrada registrada com sucesso'})
        else:
            return jsonify({'erro': 'Falha ao registrar entrada'}), 400

    except Exception as e:
        return jsonify({'erro': str(e)}), 400


@app.route('/api/saida', methods=['POST'])
@login_required
def saida_estoque():
    """Registra saída de produtos"""
    try:
        dados = request.get_json()

        sucesso = estoque.saida_estoque(
            id_produto=dados['id'],
            quantidade=int(dados['quantidade']),
            motivo=dados.get('motivo', ''),
            usuario=dados.get('usuario', '')
        )

        if sucesso:
            registrar_evento(
                tipo_evento='saida_estoque',
                descricao=f'Saída de {dados["quantidade"]} unidades do produto ID: {dados["id"]} - Motivo: {dados.get("motivo", "Não informado")}'
            )
            return jsonify({'mensagem': 'Saída registrada com sucesso'})
        else:
            return jsonify({'erro': 'Falha ao registrar saída'}), 400

    except Exception as e:
        return jsonify({'erro': str(e)}), 400


# ============================================================================
# ROTAS - RELATÓRIOS
# ============================================================================

@app.route('/api/relatorios/resumo', methods=['GET'])
@login_required
def relatorio_resumo():
    """Retorna resumo do estoque"""
    try:
        estatisticas = estoque.relatorio_valor_total()
        produtos_baixo = len(estoque.relatorio_estoque_baixo())

        # Contar categorias únicas
        produtos = estoque.listar_produtos()
        total_categorias = len(set(p.categoria for p in produtos))

        return jsonify({
            'total_produtos': estatisticas['total_produtos'],
            'total_quantidades': estatisticas['total_unidades'],
            'valor_total': estatisticas['valor_total'],
            'produtos_estoque_baixo': produtos_baixo,
            'total_categorias': total_categorias
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/relatorios/estoque-baixo', methods=['GET'])
@login_required
def relatorio_estoque_baixo():
    """Retorna produtos com estoque baixo"""
    try:
        produtos_baixos = estoque.relatorio_estoque_baixo()

        resultado = []
        for prod in produtos_baixos:
            resultado.append({
                'id': prod.id_produto,
                'nome': prod.nome,
                'quantidade': prod.quantidade,
                'minimo': prod.minimo,
                'faltam': prod.minimo - prod.quantidade,
                'categoria': prod.categoria
            })

        return jsonify(resultado)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/relatorios/por-categoria', methods=['GET'])
@login_required
def relatorio_por_categoria():
    """Retorna relatório agrupado por categoria"""
    try:
        categorias = estoque.relatorio_por_categoria()

        resultado = []
        for categoria, dados in sorted(categorias.items()):
            resultado.append({
                'categoria': categoria,
                'quantidade': dados['total_unidades'],
                'valor_total': dados['valor_total'],
                'produtos': dados['total_produtos']
            })

        return jsonify(resultado)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/relatorios/top-produtos', methods=['GET'])
@login_required
def relatorio_top_produtos():
    """Retorna top 10 produtos por valor"""
    try:
        produtos = estoque.listar_produtos()
        produtos_sorted = sorted(produtos, key=lambda p: p.valor_total(), reverse=True)[:10]

        resultado = []
        for prod in produtos_sorted:
            resultado.append({
                'id': prod.id_produto,
                'nome': prod.nome,
                'valor_total': prod.valor_total(),
                'quantidade': prod.quantidade,
                'preco': prod.preco
            })

        return jsonify(resultado)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


# ============================================================================
# TRATAMENTO DE ERROS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Erro 404"""
    return jsonify({'erro': 'Endpoint não encontrado'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Erro 500"""
    return jsonify({'erro': 'Erro interno do servidor'}), 500


# ============================================================================
# INICIALIZAÇÃO DO BANCO DE DADOS
# ============================================================================

def init_db():
    """Inicializa o banco de dados e cria as tabelas"""
    global estoque
    with app.app_context():
        try:
            db.create_all()
            print("Tabelas do banco criadas/verificadas")

            # Verificar coluna role apenas para SQLite
            if db.engine.dialect.name == 'sqlite':
                try:
                    with db.engine.connect() as conn:
                        coluna_role = conn.execute(text("PRAGMA table_info(users)"))
                        coluna_role = coluna_role.fetchall()
                        if coluna_role and 'role' not in [c[1] for c in coluna_role]:
                            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'"))
                            conn.commit()
                except:
                    pass

            # Criar usuario admin se nao existir
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(username='admin', password=generate_password_hash('admin'), role='admin')
                db.session.add(admin_user)
                db.session.commit()
                print("Usuario admin criado (login: admin / senha: admin)")
            else:
                # Se existir mas nao tiver role, atualiza
                if not admin_user.role or admin_user.role not in ['user', 'admin']:
                    admin_user.role = 'admin'
                    db.session.commit()

            # Se a senha do admin for scrypt, atualiza para um hash compatível com pbkdf2:sha256
            if admin_user and admin_user.password.startswith('scrypt:'):
                admin_user.password = generate_password_hash('admin', method='pbkdf2:sha256')
                db.session.commit()

            # Inicializar o estoque
            estoque = EstoqueDB()
            print("Banco de dados inicializado com sucesso\n")
            
        except Exception as erro:
            print(f"ERRO ao inicializar banco: {erro}")
            print("Verificar: MySQL rodando? Credenciais corretas? Banco criado?")
            raise

# Inicializar banco de dados na primeira execução
init_db()

# ============================================================================
# EXECUTAR APLICAÇÃO
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

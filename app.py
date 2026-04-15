from app import create_app

# Criar a aplicação usando o Application Factory
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
from sqlalchemy import inspect, text
from database import create_app, db, mail, DATABASE_URL
from estoque_db import EstoqueDB
from models import Produto, Movimentacao, User, Chamada, Historico
from datetime import datetime, timedelta, timezone
import os
import base64

# Criar aplicacao Flask
app, db, mail = create_app()

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
print("="*60 + "\n")

# Garantir que as colunas adicionais existam (compatibilidade com banco já em uso)
with app.app_context():
    inspector = inspect(db.engine)

    if 'chamadas' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('chamadas')]
        if 'status' not in columns:
            try:
                db.session.execute(text("ALTER TABLE chamadas ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'nova'"))
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Falha ao criar coluna status em chamadas: {e}")

    if 'users' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'localizacao' not in columns:
            try:
                db.session.execute(text("ALTER TABLE users ADD COLUMN localizacao VARCHAR(255) NOT NULL DEFAULT ''"))
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Falha ao criar coluna localizacao em users: {e}")

    # Garantir que todos os chamados têm um status válido (não NULL)
    try:
        chamadas_com_status_vazio = Chamada.query.filter(
            (Chamada.status == None) | (Chamada.status == '')
        ).all()
        
        if chamadas_com_status_vazio:
            for chamada in chamadas_com_status_vazio:
                chamada.status = 'nova'
            db.session.commit()
            print(f"Atualizados {len(chamadas_com_status_vazio)} chamados com status vazio para 'nova'")
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao limpar status de chamadas: {e}")

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
# FUNÇÃO AUXILIAR - ENVIO DE EMAILS
# ============================================================================

def carregar_logo_email():
    """Carrega o logo Soma Asset como data URI para usar no email."""
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'img', 'SOMA_logo.png')
    if os.path.exists(logo_path):
        try:
            with open(logo_path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('ascii')
            return f"data:image/png;base64,{encoded}"
        except Exception as e:
            print(f"Erro ao carregar logo para email: {e}")
    return ''


def enviar_email_notificacao(usuario, titulo, mensagem, chamada_id=None):
    """Envia email de notificação para o usuário
    
    Args:
        usuario: Objeto User com dados do usuário
        titulo: Título/Assunto do email
        mensagem: Conteúdo da mensagem
        chamada_id: ID da chamada (opcional)
    """
    try:
        # Construir email do usuário usando nome de usuário + domínio padrão
        mail_domain = os.getenv('MAIL_DOMAIN_DEFAULT', '@empresa.com')
        email_usuario = f"{usuario.username}{mail_domain}".replace('@@empresa.com', '@empresa.com')
        
        if '@' in usuario.username:
            email_usuario = usuario.username

        logo_src = carregar_logo_email()
        logo_html = f'<img src="{logo_src}" alt="Soma Asset" width="180" style="display:block; margin:0 auto 20px; max-width:100%; height:auto;" />' if logo_src else ''

        msg = Message(
            subject=titulo,
            recipients=[email_usuario],
            html=f"""
            <html>
                <body style="margin:0; padding:0; background:#eef2f7; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color:#1f1f1f;">
                    <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#eef2f7; padding:28px 0;">
                        <tr>
                            <td align="center">
                                <table width="650" cellpadding="0" cellspacing="0" role="presentation" style="background:#ffffff; border-radius:24px; overflow:hidden; border:1px solid #d8dee8; box-shadow:0 24px 54px rgba(0,0,0,0.08);">
                                    <tr>
                                        <td style="background:#000000; padding:28px 32px;">
                                            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                                                <tr>
                                                    <td style="vertical-align:middle;">{logo_html}</td>
                                                    <td style="vertical-align:middle; text-align:right; color:#ffffff; font-size:13px; letter-spacing:0.4px; text-transform:uppercase;">Soma Asset</td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="background:#f8fafc; padding:24px 32px 18px 32px; border-bottom:1px solid #e6ebf3;">
                                            <span style="display:inline-block; background:#bd9a5f; color:#000000; font-size:12px; letter-spacing:1px; text-transform:uppercase; padding:10px 14px; border-radius:999px;">Notificação</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding:0 32px 32px 32px;">
                                            <h1 style="font-size:30px; line-height:1.1; color:#111111; margin:0 0 20px;">{titulo}</h1>
                                            <p style="font-size:16px; line-height:1.8; color:#3c495b; margin:0 0 22px;">Olá <strong>{usuario.username}</strong>,</p>
                                            <p style="font-size:16px; line-height:1.8; color:#3c495b; margin:0 0 26px;">{mensagem}</p>
                                            {f'<div style="margin-bottom:24px; padding:20px; background:#ffffff; border:1px solid #e3e8f1; border-radius:20px;"> <p style="margin:0; font-size:15px; color:#4a5768;"><strong>ID do Chamado:</strong> {chamada_id}</p> </div>' if chamada_id else ''}
                                            <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin-top:0;">
                                                <tr>
                                                    <td style="width:48%; vertical-align:top; padding-right:10px;">
                                                        <div style="background:#ffffff; border:1px solid #e3e8f1; border-radius:20px; padding:18px;">
                                                            <p style="margin:0 0 10px; font-size:12px; letter-spacing:1px; text-transform:uppercase; color:#6c757d;">Status</p>
                                                            <p style="margin:0; font-size:18px; color:#000000;">{titulo}</p>
                                                        </div>
                                                    </td>
                                                    <td style="width:52%; vertical-align:top; padding-left:10px;">
                                                        <div style="background:#ffffff; border:1px solid #e3e8f1; border-radius:20px; padding:18px;">
                                                            <p style="margin:0 0 10px; font-size:12px; letter-spacing:1px; text-transform:uppercase; color:#6c757d;">Aplicativo</p>
                                                            <p style="margin:0; font-size:18px; color:#000000;">Sistema de Chamados</p>
                                                        </div>
                                                    </td>
                                                </tr>
                                            </table>
                                            <div style="margin-top:30px; padding:20px; background:#f8fafc; border-radius:20px; border:1px solid #e3e8f1;">
                                                <p style="margin:0; font-size:14px; line-height:1.7; color:#6b7280;">Este email foi gerado automaticamente pelo Sistema de Chamados Soma Asset. Não responda a esta mensagem.</p>
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
            </html>
            """
        )

        mail.send(msg)
        print(f"✓ Email enviado para {email_usuario}: {titulo}")
        return True
    except Exception as e:
        print(f"✗ Erro ao enviar email para {usuario.username}: {e}")
        return False

# ============================================================================
# ROTAS - AUTENTICAÇÃO
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if current_user.is_authenticated:
        return redirect(url_for('admin') if current_user.is_admin else url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('admin', tab='chamadas') if user.is_admin else url_for('index'))
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
            'area': user.area or '',
            'localizacao': user.localizacao or '',
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
    area = dados.get('area', '').strip()
    localizacao = dados.get('localizacao', '').strip()
    if role not in ['user', 'admin']:
        return jsonify({'erro': 'Role deve ser "user" ou "admin"'}), 400
    
    # Verificar se username já existe
    if User.query.filter_by(username=username).first():
        return jsonify({'erro': 'Username já existe'}), 400

    novo_user = User(
        username=username,
        password=generate_password_hash(password, method='pbkdf2:sha256'),
        role=role,
        area=area,
        localizacao=localizacao
    )
    db.session.add(novo_user)
    db.session.commit()
    
    registrar_evento(
        tipo_evento='usuario_criado',
        descricao=f'Usuário "{username}" criado com papel: {role} e área: {area or "Sem área"}'
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
    try:
        db.session.delete(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': 'Falha ao remover usuário. Verifique dependências e tente novamente.', 'detalhes': str(e)}), 500
    
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
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if current_user.is_admin:
        query = Chamada.query
    else:
        query = Chamada.query.filter_by(id_usuario=current_user.id)

    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Chamada.data_criacao >= start)
        except ValueError:
            return jsonify({'erro': 'Data inicial inválida'}), 400

    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Chamada.data_criacao < end)
        except ValueError:
            return jsonify({'erro': 'Data final inválida'}), 400

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            if end < start:
                return jsonify({'erro': 'A data final deve ser igual ou posterior à data inicial'}), 400
            if (end - start).days > 30:
                return jsonify({'erro': 'O período não pode exceder 30 dias'}), 400
        except ValueError:
            pass

    query = query.order_by(Chamada.data_criacao.desc())
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

    if novo_status == chamada.status:
        return jsonify({'mensagem': 'Status já está definido'}), 200

    chamada.status = novo_status
    chamada.lida = novo_status != 'nova'
    db.session.commit()

    # Enviar email de notificação ao usuário
    usuario = chamada.usuario
    if usuario:
        if novo_status == 'execucao':
            titulo = "Chamado em Execução"
            mensagem = f"Seu chamado foi iniciado e está em execução. Um administrador está trabalhando na sua solicitação."
            enviar_email_notificacao(usuario, titulo, mensagem, chamada.id_chamada)
        
        elif novo_status == 'concluida':
            titulo = "Chamado Finalizado"
            mensagem = f"Seu chamado foi finalizado com sucesso. Obrigado por usar nosso sistema!"
            enviar_email_notificacao(usuario, titulo, mensagem, chamada.id_chamada)

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

        # Contar chamadas por status - garantir que não há NULL
        chamadas_analise = Chamada.query.filter(Chamada.status == 'analise').count()
        chamadas_execucao = Chamada.query.filter(Chamada.status == 'execucao').count()
        chamadas_abertas = Chamada.query.filter(
            Chamada.status.in_(['nova', 'analise', 'execucao', 'lida'])
        ).count()
        chamadas_novas = Chamada.query.filter(Chamada.status == 'nova').count()
        
        # Chamadas finalizadas nos últimos 7 dias (criadas nos últimos 7 dias)
        data_limite = datetime.now(timezone(timedelta(hours=-3))) - timedelta(days=7)
        chamadas_finalizadas_7dias = Chamada.query.filter(
            Chamada.status == 'concluida',
            Chamada.data_criacao >= data_limite
        ).count()

        # Contar categorias únicas
        produtos = estoque.listar_produtos()
        total_categorias = len(set(p.categoria for p in produtos))

        return jsonify({
            'chamadas_analise': chamadas_analise,
            'chamadas_execucao': chamadas_execucao,
            'chamadas_abertas': chamadas_abertas,
            'chamadas_novas': chamadas_novas,
            'chamadas_finalizadas_7dias': chamadas_finalizadas_7dias,
            'produtos_estoque_baixo': produtos_baixo,
            'total_categorias': total_categorias,
            'total_produtos': estatisticas['total_produtos'],
            'total_quantidades': estatisticas['total_unidades'],
            'valor_total': estatisticas['valor_total']
        })
    except Exception as e:
        print(f"Erro ao gerar resumo: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/api/debug/chamadas-count', methods=['GET'])
@login_required
def debug_chamadas_count():
    """Endpoint de debug - mostra contagem real de chamados por status"""
    try:
        # Contar por cada status
        todos_status = Chamada.query.all()
        status_count = {}
        
        for chamada in todos_status:
            status = chamada.status if chamada.status else 'NULL'
            status_count[status] = status_count.get(status, 0) + 1
        
        # Também contar com queries explícitas
        contagens_explicitas = {
            'nova': Chamada.query.filter(Chamada.status == 'nova').count(),
            'lida': Chamada.query.filter(Chamada.status == 'lida').count(),
            'analise': Chamada.query.filter(Chamada.status == 'analise').count(),
            'execucao': Chamada.query.filter(Chamada.status == 'execucao').count(),
            'concluida': Chamada.query.filter(Chamada.status == 'concluida').count(),
        }
        
        abertas = Chamada.query.filter(
            Chamada.status.in_(['nova', 'lida', 'analise', 'execucao'])
        ).count()
        
        data_limite = datetime.now(timezone(timedelta(hours=-3))) - timedelta(days=7)
        finalizadas_7dias = Chamada.query.filter(
            Chamada.status == 'concluida',
            Chamada.data_criacao >= data_limite
        ).count()
        
        return jsonify({
            'status_count_raw': status_count,
            'contagens_explicitas': contagens_explicitas,
            'abertas_total': abertas,
            'finalizadas_7dias': finalizadas_7dias,
            'total_chamados': len(todos_status),
            'timestamp': datetime.now(timezone(timedelta(hours=-3))).isoformat()
        })
    except Exception as e:
        print(f"Erro ao gerar debug: {e}")
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

            # Verificar colunas role e area e adicionar se estiverem ausentes
            if db.engine.dialect.name == 'sqlite':
                try:
                    with db.engine.connect() as conn:
                        coluna_role = conn.execute(text("PRAGMA table_info(users)"))
                        colunas = [c[1] for c in coluna_role.fetchall()]
                        if 'role' not in colunas:
                            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'"))
                        if 'area' not in colunas:
                            conn.execute(text("ALTER TABLE users ADD COLUMN area VARCHAR(255) DEFAULT ''"))
                        conn.commit()
                except:
                    pass
            else:
                try:
                    with db.engine.connect() as conn:
                        coluna_area = conn.execute(text("SHOW COLUMNS FROM users LIKE 'area'"))
                        if coluna_area.fetchone() is None:
                            conn.execute(text("ALTER TABLE users ADD COLUMN area VARCHAR(255) DEFAULT ''"))
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
    app.run(debug=False, host='0.0.0.0', port=5000)

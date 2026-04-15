from flask import Flask, render_template_string
from flask_login import LoginManager
from flask_mail import Message
from sqlalchemy import inspect, text
from .database import create_app as create_db_app, db, mail
from .migrate import migrate
from .models import Produto, Movimentacao, User, Chamada, Historico
from .services import EstoqueService
from .auth import can_perform, get_user_permissions, ROLES_PERMISSIONS
from datetime import datetime, timedelta, timezone
import os

# Instância global do serviço de estoque
estoque = None

def create_app():
    """Application Factory Pattern"""
    global estoque

    # Criar app com database
    app, db, mail = create_db_app()

    # Configurar LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Registrar blueprints
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.admin import admin_bp
    from .routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Adicionar funções úteis ao contexto de templates
    @app.context_processor
    def inject_auth():
        """Injetar funções de auth nos templates"""
        return {
            'can_perform': can_perform,
            'get_user_permissions': get_user_permissions,
            'ROLES_PERMISSIONS': ROLES_PERMISSIONS
        }

    # Registrar erros
    @app.errorhandler(403)
    def forbidden(e):
        """Erro de acesso negado"""
        return render_template_string('<h1>Acesso Negado (403)</h1><p>Você não tem permissão para acessar este recurso.</p>'), 403
    
    @app.errorhandler(404)
    def not_found(e):
        """Erro de página não encontrada"""
        return render_template_string('<h1>Página Não Encontrada (404)</h1><p>O recurso que você procura não existe.</p>'), 404

    # Inicializar Flask-Migrate
    migrate.init_app(app, db)

    # Inicializar banco e serviços
    with app.app_context():
        init_database()

    return app

def init_database():
    """Inicializa o banco de dados e cria dados iniciais"""
    global estoque

    # Exibir informações de configuração
    print("\n" + "="*60)
    print("Sistema de Estoque - Inicializando...")
    print("="*60)
    from .database import DATABASE_URL
    if "mysql" in DATABASE_URL:
        db_type = "MySQL"
    elif "sqlite" in DATABASE_URL:
        db_type = "SQLite"
    else:
        db_type = "Desconhecido"
    print(f"Banco de dados: {db_type}")
    print("="*60 + "\n")

    #Aplicar migracoes se existirem
    try:
        migrations_dir = os.path.join(os.path.dirname(__file__), '..', 'migrations')
        if os.path.exists(os.path.join(migrations_dir, 'versions')):
            from flask_migrate import upgrade
            print("Aplicando migracoes do banco de dados...")
            upgrade(revision='head')
    except Exception as e:
        print("[INFO] Nota: {}".format(e))
        print("Criando tabelas padrao...")
        db.create_all()

    # Criar usuário admin se não existir
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(username='admin', password=generate_password_hash('admin'), role='admin')
        db.session.add(admin_user)
        db.session.commit()
        print("Usuario admin criado (login: admin / senha: admin)")
    else:
        # Se existir mas não tiver role, atualiza
        if not admin_user.role or admin_user.role not in ['user', 'admin']:
            admin_user.role = 'admin'
            db.session.commit()

    # Se a senha do admin for scrypt, atualiza para um hash compatível
    if admin_user and admin_user.password.startswith('scrypt:'):
        admin_user.password = generate_password_hash('admin', method='pbkdf2:sha256')
        db.session.commit()

    # Inicializar o estoque
    estoque = EstoqueService()
    print("Banco de dados inicializado com sucesso\n")
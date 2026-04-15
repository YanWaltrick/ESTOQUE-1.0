import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from dotenv import load_dotenv

# Carregar variaveis de ambiente
load_dotenv()

# Configuracao do banco de dados
# Suporta MySQL (mysql+pymysql), SQLite local e URL customizada
def get_database_url():
    """Obtem URL do banco.

    Suporta MySQL e SQLite. Se DATABASE_URL não estiver definida,
    usa SQLite por padrão.
    """
    db_url = os.getenv('DATABASE_URL')

    if not db_url:
        # Usar SQLite por padrão se não houver configuração
        db_url = 'sqlite:///estoque.db'

    # Aceita MySQL, SQLite ou outros drivers explícitos.
    return db_url

DATABASE_URL = get_database_url()

# Instancia do SQLAlchemy
db = SQLAlchemy()

# Instancia do Flask-Mail
mail = Mail()

def create_app():
    """Factory function para criar a aplicacao Flask"""
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static',
                static_url_path='/static')

    # Configuracoes
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-secreta-desenvolvimento')
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False} if 'sqlite' in DATABASE_URL else {}
    }

    # Configuracoes de Email
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))

    # Inicializar banco de dados e email
    db.init_app(app)
    mail.init_app(app)

    return app, db, mail
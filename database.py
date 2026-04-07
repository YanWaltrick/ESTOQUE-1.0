import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Carregar variaveis de ambiente
load_dotenv()

# Configuracao do banco de dados
# Suporta MySQL (mysql+pymysql), SQLite local e URL customizada
def get_database_url():
    """Obtem URL do banco.

    MySQL é obrigatório neste modo. Se DATABASE_URL não estiver definida,
    a aplicação sai com mensagem de orientação.
    """
    db_url = os.getenv('DATABASE_URL')

    if not db_url:
        raise RuntimeError(
            "NENHUM DATABASE_URL configurado.\n"
            "Defina no .env (ou variável de ambiente) a URL MySQL, ex:\n"
            "DATABASE_URL=mysql+pymysql://estoque_user:12345@localhost:3306/estoque_db"
        )

    if db_url.startswith('sqlite'):
        raise RuntimeError(
            "SQLite não está habilitado.\n"
            "Altere DATABASE_URL para MySQL no .env:\n"
            "DATABASE_URL=mysql+pymysql://estoque_user:12345@localhost:3306/estoque_db"
        )

    # Aceita MySQL ou outros drivers explícitos se o usuário quiser.
    return db_url

DATABASE_URL = get_database_url()

# Instancia do SQLAlchemy
db = SQLAlchemy()

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

    # Inicializar banco de dados
    db.init_app(app)

    return app, db
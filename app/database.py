import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env no diretório principal do projeto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Configuração do banco de dados
# O projeto é padronizado em MySQL (mysql+pymysql) em TODOS os ambientes
# (dev, teste, produção). Ver docs/banco-de-dados/PLANO_PADRONIZACAO_MYSQL.md.
def get_database_url():
    """Obtém a URL do banco a partir de DATABASE_URL.

    O projeto usa MySQL em todos os ambientes. `DATABASE_URL` é obrigatória — não
    há mais fallback para SQLite. Em dev/teste, suba o MySQL via
    `docker compose up` (ver docker-compose.yml).
    """
    db_url = os.getenv('DATABASE_URL')

    if not db_url:
        raise RuntimeError(
            'DATABASE_URL não definida. Configure-a (ex.: '
            'mysql+pymysql://estoque:estoque123@127.0.0.1:3306/estoque_db). '
            'Em dev/teste, suba o MySQL com `docker compose up`.'
        )

    # Normaliza URLs MySQL sem driver explícito para usar PyMySQL
    if db_url.startswith('mysql://'):
        db_url = db_url.replace('mysql://', 'mysql+pymysql://', 1)

    return db_url

DATABASE_URL = get_database_url()

# Instancia do SQLAlchemy
db = SQLAlchemy()

# Instancia do Flask-Mail
mail = Mail()

def create_app():
    """Factory function para criar a aplicacao Flask"""
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static',
                static_url_path='/static')

    # Configuracoes
    # Em produção, REQUIRE que SECRET_KEY esteja definida.
    secret = os.getenv('SECRET_KEY')
    if not secret and os.getenv('FLASK_ENV') != 'development':
        raise RuntimeError('SECRET_KEY não definida. Configure SECRET_KEY em variáveis de ambiente.')
    app.config['SECRET_KEY'] = secret or 'chave-secreta-desenvolvimento'
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,   # detecta conexões MySQL ociosas/derrubadas
        'pool_recycle': 280,     # recicla antes do wait_timeout padrão do MySQL
    }

    # Cookies de sessão seguros (não forçar em development para facilitar testes locais)
    is_dev = os.getenv('FLASK_ENV') == 'development'
    app.config['SESSION_COOKIE_SECURE'] = False if is_dev else os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    # Em desenvolvimento, usar 'None' para permitir acesso remoto (sem HTTPS)
    # Em produção com HTTPS, usar 'None' com SESSION_COOKIE_SECURE=True
    # Para localhost apenas, pode usar 'Lax'
    app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'None' if is_dev else 'Lax')

    # Configuracoes de Email
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))
    app.config['ADMIN_EMAILS'] = os.getenv('ADMIN_EMAILS', '')
    app.config['TEAMS_CHANNEL_WEBHOOK_URL'] = os.getenv('TEAMS_CHANNEL_WEBHOOK_URL', '')
    app.config['POWER_AUTOMATE_WEBHOOK_URL'] = os.getenv('POWER_AUTOMATE_WEBHOOK_URL', '')
    app.config['APP_PUBLIC_BASE_URL'] = os.getenv('APP_PUBLIC_BASE_URL', '')
    app.config['POWER_AUTOMATE_TIMEOUT_SECONDS'] = int(os.getenv('POWER_AUTOMATE_TIMEOUT_SECONDS', 10))

    # Inicializar banco de dados e email
    db.init_app(app)
    mail.init_app(app)

    return app, db, mail
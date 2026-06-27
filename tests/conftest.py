"""Configuração base do pytest para a aplicação de estoque.

Este arquivo É o padrão de testes do projeto: qualquer teste novo deve
reutilizar as fixtures definidas aqui em vez de montar sua própria app ou
banco. Veja `tests/test_smoke.py` como exemplo canônico.

Pontos-chave da arquitetura de teste:

- `DATABASE_URL` é resolvida no momento em que `app.database` é importado.
  Por isso, definimos um SQLite temporário em variável de ambiente ANTES de
  qualquer import da aplicação. `load_dotenv` não sobrescreve variáveis já
  presentes no ambiente, então este valor vence um eventual `.env`.
- `create_app()` chama `init_database()` na criação (cria tabelas e o usuário
  admin padrão). A app é criada uma vez por sessão de testes.
- Cada teste roda dentro de uma transação revertida ao final (`db_session`),
  garantindo isolamento sem recriar o banco a cada teste.
"""

import os
import tempfile

import pytest

# --- Configuração de ambiente (antes de importar a aplicação) ----------------
# Banco de teste isolado em arquivo temporário (não toca instance/estoque.sqlite).
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".sqlite", prefix="estoque-test-")
os.close(_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["FLASK_ENV"] = "development"  # evita exigir SECRET_KEY e HSTS
os.environ.setdefault("SECRET_KEY", "chave-de-teste")

# Imports da aplicação só depois de configurar o ambiente acima.
from app import create_app  # noqa: E402
from app.database import db as _db  # noqa: E402


@pytest.fixture(scope="session")
def app():
    """Instância única da aplicação Flask configurada para testes."""
    application = create_app()
    application.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,  # permite POSTs em testes sem token CSRF
    )

    yield application

    # Limpeza do arquivo de banco temporário ao fim da sessão.
    if os.path.exists(_DB_PATH):
        os.remove(_DB_PATH)


@pytest.fixture()
def db_session(app):
    """Isola cada teste em uma transação revertida ao final.

    Liga a sessão do Flask-SQLAlchemy a uma conexão com transação externa.
    `join_transaction_mode="create_savepoint"` faz com que commits dentro do
    teste virem savepoints, desfeitos pelo rollback final — nada vaza entre
    testes nem persiste no banco.
    """
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()

        _db.session.remove()
        _db.session.configure(
            bind=connection,
            join_transaction_mode="create_savepoint",
        )

        yield _db.session

        _db.session.remove()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(app):
    """Cliente HTTP de teste, sem autenticação."""
    return app.test_client()


@pytest.fixture()
def auth_client(app, db_session):
    """Cliente HTTP já autenticado como o admin padrão (admin/admin)."""
    test_client = app.test_client()
    response = test_client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )
    # Login bem-sucedido redireciona (302); falha re-renderiza o form (200).
    assert response.status_code == 302, "Falha ao autenticar o admin de teste"
    return test_client

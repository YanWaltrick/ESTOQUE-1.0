"""Configuração base do pytest para a aplicação de estoque.

Este arquivo É o padrão de testes do projeto: qualquer teste novo deve
reutilizar as fixtures definidas aqui em vez de montar sua própria app ou
banco. Veja `tests/test_smoke.py` como exemplo canônico.

Pontos-chave da arquitetura de teste:

- O projeto é 100% MySQL. Os testes usam um banco DEDICADO (`estoque_test`) no
  mesmo container de dev (ver `docker-compose.yml`). **Pré-requisito:** o MySQL
  precisa estar de pé (`docker compose up -d`).
- `DATABASE_URL` é resolvida no momento em que `app.database` é importado. Por
  isso, definimos a URL de teste em variável de ambiente ANTES de qualquer import
  da aplicação. `load_dotenv` não sobrescreve variáveis já presentes no ambiente,
  então este valor vence o `.env` (blinda contra apontar para dev/produção).
  Pode ser sobrescrita via `TEST_DATABASE_URL` (ex.: no CI).
- `create_app()` chama `init_database()` na criação (cria tabelas e o usuário
  admin padrão). A app é criada uma vez por sessão de testes.
- Cada teste roda dentro de uma transação externa revertida ao final
  (`db_session`), garantindo isolamento sem recriar o banco a cada teste.
"""

import glob
import os

import pytest

# --- Configuração de ambiente (antes de importar a aplicação) ----------------
# Banco de teste DEDICADO em MySQL (estoque_test). Nunca aponta para o banco de
# dev/produção. Sobrescrevível via TEST_DATABASE_URL.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "mysql+pymysql://estoque:estoque123@127.0.0.1:3306/estoque_test?charset=utf8mb4",
)
os.environ["FLASK_ENV"] = "development"  # evita exigir SECRET_KEY e HSTS
os.environ.setdefault("SECRET_KEY", "chave-de-teste")

# Imports da aplicação só depois de configurar o ambiente acima.
from app import create_app  # noqa: E402
from app.database import db as _db  # noqa: E402

# `tests/test_entra_id.py` é um smoke legado baseado em `print`, executável só
# via `python tests/test_entra_id.py` (ver CLAUDE.md). Não tem funções `test_*`
# e seu corpo de módulo chama `create_app()`/`exit(1)` no import — então é
# ignorado pela coleta do pytest para não rodar esses efeitos colaterais.
collect_ignore = ["test_entra_id.py"]


# Subpastas de upload tocadas pelos testes (foto de perfil, documentos, fotos de
# equipamento e PDFs de termo). Os caminhos são relativos à raiz do projeto, que
# é o diretório-pai de `tests/`.
_UPLOAD_SUBDIRS = [
    os.path.join("static", "uploads", "avatars"),
    os.path.join("static", "uploads", "documentos"),
    os.path.join("static", "uploads", "chamadas"),
    os.path.join("static", "uploads", "termos"),
    os.path.join("static", "uploads", "documentos", "termos"),
]


@pytest.fixture(scope="session", autouse=True)
def _limpar_uploads_de_teste():
    """Remove arquivos que os testes gravam em `static/uploads/`.

    Vários testes exercitam upload de foto/documento e geração de PDF do termo,
    que escrevem em disco **fora** da transação de banco (revertida pelo
    `db_session`). Para não poluir o working tree, tiramos um snapshot do que já
    existia e, ao fim da sessão, removemos apenas os arquivos novos — preservando
    qualquer upload legado versionado.
    """
    raiz = os.path.dirname(os.path.dirname(__file__))
    antes = set()
    for sub in _UPLOAD_SUBDIRS:
        antes.update(glob.glob(os.path.join(raiz, sub, "*")))

    yield

    for sub in _UPLOAD_SUBDIRS:
        for caminho in glob.glob(os.path.join(raiz, sub, "*")):
            if caminho not in antes and os.path.isfile(caminho):
                try:
                    os.remove(caminho)
                except OSError:
                    pass


@pytest.fixture(scope="session")
def app():
    """Instância única da aplicação Flask configurada para testes."""
    application = create_app()
    application.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,  # permite POSTs em testes sem token CSRF
    )

    yield application

    # Banco de teste é o estoque_test (MySQL, container) — nada a remover aqui.
    # O isolamento por teste fica a cargo da fixture `db_session`.


@pytest.fixture()
def db_session(app):
    """Isola cada teste em uma transação externa revertida ao final.

    Segue a receita oficial do Flask-SQLAlchemy para *join an external
    transaction*: cada engine é temporariamente substituída por uma conexão
    com transação aberta. Isso é necessário porque o `get_bind` do
    Flask-SQLAlchemy resolve o engine padrão direto via `engines[None]` e
    **ignora** `Session.configure(bind=...)`; só trocando a entrada do
    dicionário de engines é que TODO o trabalho da sessão — inclusive commits,
    que viram savepoints — passa a rodar dentro da transação e é desfeito pelo
    rollback final. As engines originais são restauradas no teardown.
    """
    with app.app_context():
        engines = _db.engines
        originais = dict(engines)
        conexoes = []
        for key, engine in originais.items():
            connection = engine.connect()
            transaction = connection.begin()
            engines[key] = connection
            conexoes.append((connection, transaction))

        _db.session.remove()  # garante sessão nova ligada à conexão
        try:
            yield _db.session
        finally:
            _db.session.remove()
            for connection, transaction in conexoes:
                if transaction.is_active:
                    transaction.rollback()
                connection.close()
            engines.update(originais)


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


# --- Fixtures auxiliares para os testes de cobertura -------------------------
# Importadas aqui (após a configuração de ambiente acima) para criar usuários de
# teste com senha conhecida e clientes autenticados como usuário comum.
from app.auth.security import PasswordValidator  # noqa: E402
from app.models import User  # noqa: E402

# Senha padrão usada pelos usuários de teste — atende ao PasswordValidator
# (>=6 chars, maiúscula, minúscula e dígito).
SENHA_TESTE = "Senha123"

# Hash pré-computado da senha padrão. O KDF (pbkdf2) é deliberadamente lento;
# computá-lo uma única vez evita repetir o custo em cada usuário criado pela
# factory (centenas de vezes ao longo da suíte).
_SENHA_TESTE_HASH = PasswordValidator.hash_password(SENHA_TESTE)


@pytest.fixture()
def criar_usuario(db_session):
    """Factory de usuários de teste com senha já hasheada.

    Uso: `user = criar_usuario(username="joao", role="usuario")`. A senha
    padrão é `SENHA_TESTE` (hash pré-computado); passe `senha=` para
    sobrescrever. Demais kwargs são repassados ao construtor de `User`
    (tipo_contrato, email, empresa, etc.).
    """

    def _criar(username="usuario_teste", senha=None, role="usuario", **kwargs):
        password = _SENHA_TESTE_HASH if senha is None else PasswordValidator.hash_password(senha)
        user = User(
            username=username,
            password=password,
            role=role,
            **kwargs,
        )
        db_session.add(user)
        db_session.commit()
        return user

    return _criar


@pytest.fixture()
def admin_user(db_session):
    """O usuário admin padrão (`admin`) semeado na inicialização do banco."""
    return User.query.filter_by(username="admin").first()


@pytest.fixture()
def usuario_comum(criar_usuario):
    """Um usuário comum (role='usuario') persistido para o teste."""
    return criar_usuario(username="usuario_comum", role="usuario")


@pytest.fixture()
def user_client(app, usuario_comum):
    """Cliente HTTP autenticado como um usuário comum (não admin)."""
    test_client = app.test_client()
    response = test_client.post(
        "/login",
        data={"username": usuario_comum.username, "password": SENHA_TESTE},
        follow_redirects=False,
    )
    assert response.status_code == 302, "Falha ao autenticar o usuário comum de teste"
    return test_client


@pytest.fixture()
def perfil_verificado_client(user_client):
    """`user_client` com a reautenticação de perfil já marcada na sessão.

    Evita repetir o bloco `with ... session_transaction()` em cada teste de
    `/perfil/*` que exige `perfil_verified` na sessão.
    """
    with user_client.session_transaction() as sess:
        sess["perfil_verified"] = True
    return user_client

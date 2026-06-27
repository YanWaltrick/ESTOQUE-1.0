"""Testes de fumaça que validam a base de testes e o fluxo de autenticação.

Servem de exemplo canônico: copie o estilo destes testes ao escrever novos.
"""


def test_login_redireciona_quando_nao_autenticado(client):
    """Acessar o dashboard sem login deve redirecionar para a tela de login."""
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_admin_com_credenciais_validas(client, db_session):
    """Login do admin padrão deve autenticar e redirecionar para a área admin."""
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/admin" in response.headers["Location"]


def test_login_admin_com_senha_invalida(client, db_session):
    """Senha incorreta deve re-renderizar o login (200), sem redirecionar."""
    response = client.post(
        "/login",
        data={"username": "admin", "password": "senha-errada"},
        follow_redirects=False,
    )

    assert response.status_code == 200


def test_dashboard_acessivel_apos_login(auth_client):
    """Com o admin autenticado, o dashboard deve responder 200."""
    response = auth_client.get("/")

    assert response.status_code == 200

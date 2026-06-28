"""Testes da integração Microsoft Entra ID.

Cobrem `app/auth/entra_id.py` (config, helpers de usuário, cliente com MSAL
mockado) e os caminhos de erro das rotas em `app/routes/entra_auth.py` — sem
depender de credenciais Entra reais nem de rede.
"""

import pytest

from app.auth import entra_id as ei
from app.routes.entra_auth import get_entra_user_info, is_entra_authenticated


# --- create_csrf_token ------------------------------------------------------


def test_create_csrf_token():
    token = ei.create_csrf_token()
    assert isinstance(token, str)
    assert len(token) == 64  # 32 bytes em hex
    assert ei.create_csrf_token() != token


# --- EntraIDConfig ----------------------------------------------------------


def test_config_sem_variaveis_levanta(monkeypatch):
    monkeypatch.delenv("ENTRA_CLIENT_ID", raising=False)
    monkeypatch.delenv("ENTRA_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("ENTRA_TENANT_ID", raising=False)
    with pytest.raises(ValueError):
        ei.EntraIDConfig()


def test_config_com_variaveis(monkeypatch):
    monkeypatch.setenv("ENTRA_CLIENT_ID", "cid")
    monkeypatch.setenv("ENTRA_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ENTRA_TENANT_ID", "tenant")
    config = ei.EntraIDConfig()
    assert config.client_id == "cid"
    uri = config.get_redirect_uri("http://localhost:5000")
    assert uri == "http://localhost:5000/entra-callback"


# --- EntraIDClient (MSAL mockado) -------------------------------------------


@pytest.fixture()
def config_valida(monkeypatch):
    monkeypatch.setenv("ENTRA_CLIENT_ID", "cid")
    monkeypatch.setenv("ENTRA_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ENTRA_TENANT_ID", "tenant")
    return ei.EntraIDConfig()


@pytest.fixture()
def client_mock(monkeypatch, config_valida):
    class FakeMsalApp:
        def get_authorization_request_url(self, scopes, redirect_uri, state):
            return f"https://login.test/authorize?state={state}"

    monkeypatch.setattr(ei.msal, "ConfidentialClientApplication", lambda **kw: FakeMsalApp())
    return ei.EntraIDClient(config_valida)


def test_get_auth_url(client_mock):
    url = client_mock.get_auth_url("http://localhost:5000", state="abc")
    assert "state=abc" in url


def test_get_logout_url(client_mock):
    url = client_mock.get_logout_url("http://localhost:5000/")
    assert "oauth2/v2.0/logout" in url
    assert "post_logout_redirect_uri" in url


def test_get_user_info_sucesso(client_mock, monkeypatch):
    class FakeResp:
        status_code = 200

        def json(self):
            return {
                "id": "123",
                "displayName": "Fulano",
                "mail": "fulano@example.com",
                "userPrincipalName": "fulano@example.com",
            }

    monkeypatch.setattr(ei.requests, "get", lambda *a, **k: FakeResp())
    info = client_mock.get_user_info({"access_token": "tok"})
    assert info["email"] == "fulano@example.com"
    assert info["name"] == "Fulano"


def test_get_user_info_sem_access_token(client_mock):
    assert client_mock.get_user_info({}) is None


def test_get_user_info_erro_http(client_mock, monkeypatch):
    class FakeResp:
        status_code = 403

        def json(self):
            return {}

    monkeypatch.setattr(ei.requests, "get", lambda *a, **k: FakeResp())
    assert client_mock.get_user_info({"access_token": "tok"}) is None


# --- create_or_update_user_from_entra_info ----------------------------------


def test_create_user_from_entra_none():
    assert ei.create_or_update_user_from_entra_info(None) is None


def test_create_user_from_entra_sem_email():
    assert ei.create_or_update_user_from_entra_info({"name": "X"}) is None


def test_create_user_from_entra_inexistente(db_session):
    info = {"email": "naoexiste@example.com", "name": "X"}
    assert ei.create_or_update_user_from_entra_info(info) is None


def test_create_user_from_entra_por_email(db_session, criar_usuario):
    criar_usuario(username="entra1", email="entra1@example.com")
    user = ei.create_or_update_user_from_entra_info({"email": "entra1@example.com"})
    assert user is not None
    assert user.username == "entra1"


def test_create_user_from_entra_inativo(db_session, criar_usuario):
    u = criar_usuario(username="entra_inativo", email="inativo@example.com")
    u.ativo = False
    db_session.commit()
    assert ei.create_or_update_user_from_entra_info({"email": "inativo@example.com"}) is None


# --- validate_email_in_database ---------------------------------------------


def test_validate_email_in_database_vazio(db_session):
    assert ei.validate_email_in_database("") is False


def test_validate_email_in_database_existente(db_session, criar_usuario):
    criar_usuario(username="valida_email", email="valida@example.com")
    assert ei.validate_email_in_database("valida@example.com") is True


def test_validate_email_in_database_inexistente(db_session):
    assert ei.validate_email_in_database("ninguem@example.com") is False


# --- Rotas: caminhos de erro (sem config Entra) -----------------------------


def test_login_entra_sem_config_redireciona(client):
    resp = client.get("/login/entra", follow_redirects=False)
    assert resp.status_code == 302


def test_callback_sem_state_redireciona(client):
    resp = client.get("/entra-callback", follow_redirects=False)
    assert resp.status_code == 302


def test_callback_com_erro(client):
    with client.session_transaction() as sess:
        sess["entra_csrf_token"] = "tok"
    resp = client.get(
        "/entra-callback?state=tok&error=access_denied", follow_redirects=False
    )
    assert resp.status_code == 302


def test_callback_sem_code(client):
    with client.session_transaction() as sess:
        sess["entra_csrf_token"] = "tok"
    resp = client.get("/entra-callback?state=tok", follow_redirects=False)
    assert resp.status_code == 302


def test_entra_logout(client):
    resp = client.get("/entra-logout", follow_redirects=False)
    assert resp.status_code == 302


# --- Helpers de sessão ------------------------------------------------------


def test_is_entra_authenticated_false(app):
    with app.test_request_context():
        assert is_entra_authenticated() is False


def test_get_entra_user_info_none(app):
    with app.test_request_context():
        assert get_entra_user_info() is None

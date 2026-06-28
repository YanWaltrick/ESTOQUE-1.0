"""Testes de `app/services/notification_service.py`.

Cobrem a montagem de payload (AdaptiveCard e legacy), os helpers de status e o
envio ao webhook (com `urlopen` mockado). Usam `db_session` (que fornece app
context) para construir uma `Chamada` com usuário associado.
"""

from urllib.error import HTTPError, URLError

import pytest

from app.models import Chamada
from app.services import notification_service as ns


@pytest.fixture()
def chamada(db_session, criar_usuario):
    """Uma chamada persistida, ligada a um usuário com e-mail válido."""
    user = criar_usuario(username="solicitante", email="solicitante@example.com")
    c = Chamada(id_usuario=user.id, mensagem="Notebook com defeito")
    db_session.add(c)
    db_session.commit()
    return c


# --- helpers ----------------------------------------------------------------


def test_normalizar_lista_emails_filtra_invalidos():
    resultado = ns._normalizar_lista_emails("a@x.com, invalido, b@y.com")
    assert resultado == ["a@x.com", "b@y.com"]


def test_normalizar_lista_emails_vazio():
    assert ns._normalizar_lista_emails("") == []


@pytest.mark.parametrize(
    "status,esperado",
    [
        ("concluida", "Concluída"),
        ("execucao", "Em execução"),
        ("analise", "Em análise"),
        ("lida", "Lida"),
        ("nova", "Nova"),
    ],
)
def test_obter_label_status(status, esperado):
    assert ns._obter_label_status(status) == esperado


@pytest.mark.parametrize(
    "status,esperado",
    [
        ("concluida", "good"),
        ("execucao", "attention"),
        ("nova", "warning"),
        ("desconhecido", "default"),
    ],
)
def test_obter_cor_status(status, esperado):
    assert ns._obter_cor_status(status) == esperado


# --- montar_payload_notificacao_chamada -------------------------------------


def test_payload_adaptive_card(chamada):
    payload = ns.montar_payload_notificacao_chamada(chamada, "chamada_criada")
    assert payload["type"] == "message"
    assert payload["attachments"][0]["contentType"].startswith("application/vnd.microsoft.card")
    conteudo = payload["attachments"][0]["content"]
    assert conteudo["type"] == "AdaptiveCard"
    assert conteudo["body"]


def test_payload_legacy(chamada):
    payload = ns.montar_payload_notificacao_chamada(
        chamada, "chamada_criada", modo="legacy"
    )
    assert payload["origem"] == "estoque"
    assert payload["evento"] == "chamada_criada"
    assert payload["chamada"]["mensagem"] == "Notebook com defeito"
    assert payload["destinatarios"]["solicitante"] == "solicitante@example.com"


# --- enviar_notificacao_chamada ---------------------------------------------


def test_enviar_sem_webhook_configurado(chamada, monkeypatch):
    # Sem URLs de webhook, retorna sucesso silencioso.
    from flask import current_app

    monkeypatch.setitem(current_app.config, "TEAMS_CHANNEL_WEBHOOK_URL", "")
    monkeypatch.setitem(current_app.config, "POWER_AUTOMATE_WEBHOOK_URL", "")
    ok, erro = ns.enviar_notificacao_chamada(chamada, "chamada_criada")
    assert ok is True
    assert erro == ""


def test_enviar_com_webhook_sucesso(chamada, monkeypatch):
    from flask import current_app

    monkeypatch.setitem(current_app.config, "TEAMS_CHANNEL_WEBHOOK_URL", "http://webhook.test/x")

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"ok"

    monkeypatch.setattr(ns, "urlopen", lambda req, timeout=None: FakeResp())
    ok, erro = ns.enviar_notificacao_chamada(chamada, "chamada_criada")
    assert ok is True
    assert erro == ""


def test_enviar_com_http_error(chamada, monkeypatch):
    from flask import current_app

    monkeypatch.setitem(current_app.config, "TEAMS_CHANNEL_WEBHOOK_URL", "http://webhook.test/x")

    def raise_http(req, timeout=None):
        raise HTTPError("http://webhook.test/x", 500, "Internal Server Error", None, None)

    monkeypatch.setattr(ns, "urlopen", raise_http)
    ok, erro = ns.enviar_notificacao_chamada(chamada, "chamada_criada")
    assert ok is False
    assert "500" in erro


def test_enviar_com_url_error(chamada, monkeypatch):
    from flask import current_app

    monkeypatch.setitem(current_app.config, "TEAMS_CHANNEL_WEBHOOK_URL", "http://webhook.test/x")

    def raise_url(req, timeout=None):
        raise URLError("connection refused")

    monkeypatch.setattr(ns, "urlopen", raise_url)
    ok, erro = ns.enviar_notificacao_chamada(chamada, "chamada_criada")
    assert ok is False
    assert erro

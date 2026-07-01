"""Testes de `app/utils/logger.py`.

Cobrem a criação de logger e as funções de registro estruturado. Usam o
fixture `caplog` do pytest para inspecionar as mensagens emitidas.
"""

import logging

from app.utils.logger import (
    criar_logger,
    log_resposta_http,
    registrar_auditoria,
    registrar_erro,
    registrar_seguranca,
)


def test_criar_logger_idempotente():
    l1 = criar_logger("teste_app_unico")
    n_handlers = len(l1.handlers)
    l2 = criar_logger("teste_app_unico")
    assert l1 is l2
    # Configura pelo menos um handler e não os duplica em chamadas repetidas
    # (sem fixar a contagem exata, que depende da config global do logging).
    assert n_handlers > 0
    assert len(l2.handlers) == n_handlers


def test_criar_logger_nivel_debug():
    logger = criar_logger("teste_nivel")
    assert logger.level == logging.DEBUG


def test_registrar_erro_sem_contexto(caplog):
    logger = logging.getLogger("teste_erro_1")
    with caplog.at_level(logging.ERROR, logger="teste_erro_1"):
        registrar_erro(logger, ValueError("falhou"))
    assert "ValueError: falhou" in caplog.text


def test_registrar_erro_com_contexto(caplog):
    logger = logging.getLogger("teste_erro_2")
    with caplog.at_level(logging.ERROR, logger="teste_erro_2"):
        registrar_erro(logger, KeyError("chave"), {"user": "admin"})
    assert "KeyError" in caplog.text
    assert "Contexto" in caplog.text
    assert "admin" in caplog.text


def test_registrar_auditoria_completa(caplog):
    logger = logging.getLogger("teste_audit")
    with caplog.at_level(logging.INFO, logger="teste_audit"):
        registrar_auditoria(
            logger, "admin", "CREATE", tabela="users", registro_id=5, detalhes="novo"
        )
    assert "[AUDITORIA]" in caplog.text
    assert "admin" in caplog.text
    assert "users#5" in caplog.text
    assert "novo" in caplog.text


def test_registrar_auditoria_minima(caplog):
    logger = logging.getLogger("teste_audit2")
    with caplog.at_level(logging.INFO, logger="teste_audit2"):
        registrar_auditoria(logger, "admin", "LOGIN")
    assert "[AUDITORIA] admin | LOGIN" in caplog.text


def test_registrar_seguranca(caplog):
    logger = logging.getLogger("teste_seg")
    with caplog.at_level(logging.WARNING, logger="teste_seg"):
        registrar_seguranca(logger, "failed_login", usuario="attacker", detalhes="3 tentativas")
    assert "[SEGURANÇA]" in caplog.text
    assert "failed_login" in caplog.text
    assert "attacker" in caplog.text


def test_log_resposta_http_loga_status(app, caplog, monkeypatch):
    """O decorator de after_request loga método, path e status."""
    logger = logging.getLogger("teste_http")
    # `caplog` captura via propagação ao root; restauramos `propagate` ao final
    # (monkeypatch) para não vazar a mutação para outros testes.
    monkeypatch.setattr(logger, "propagate", True)

    @log_resposta_http(logger)
    def handler(response):
        return response

    with app.test_request_context("/rota-teste", method="GET"):

        class FakeResponse:
            status_code = 200

        with caplog.at_level(logging.DEBUG, logger="teste_http"):
            handler(FakeResponse())

    assert "HTTP 200" in caplog.text
    assert "/rota-teste" in caplog.text

"""
Módulo centralizado de logging para a aplicação.
Oferece logging estruturado com níveis de severidade, timestamps e contexto.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from functools import wraps


def criar_logger(nome_app: str = "estoque") -> logging.Logger:
    """
    Cria um logger centralizado com handlers para arquivo e console.

    Args:
        nome_app: Nome da aplicação (padrão: 'estoque')

    Returns:
        logger: Objeto Logger configurado
    """
    logger = logging.getLogger(nome_app)

    # Evitar duplicação de handlers se já existir
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Diretório de logs
    log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Formato estruturado para logs
    formato = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler de arquivo com rotação (máx 10MB, guardando 7 backups)
    arquivo_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, f"{nome_app}.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=7,
    )
    arquivo_handler.setLevel(logging.DEBUG)
    arquivo_handler.setFormatter(formato)
    logger.addHandler(arquivo_handler)

    # Handler de console apenas para WARNING e acima (não poluir stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formato)
    logger.addHandler(console_handler)

    return logger


def registrar_erro(logger: logging.Logger, excecao: Exception, contexto: dict = None):
    """
    Registra uma exceção com contexto estruturado.

    Args:
        logger: Logger a usar
        excecao: Exceção capturada
        contexto: Dicionário opcional com informações adicionais
    """
    msg = f"{type(excecao).__name__}: {str(excecao)}"
    if contexto:
        msg += f" | Contexto: {contexto}"
    logger.error(msg, exc_info=True)


def registrar_auditoria(
    logger: logging.Logger,
    usuario: str,
    acao: str,
    tabela: str = None,
    registro_id: int = None,
    detalhes: str = None,
):
    """
    Registra eventos de auditoria (ações de usuários).

    Args:
        logger: Logger a usar
        usuario: Nome/ID do usuário
        acao: Tipo de ação (CREATE, UPDATE, DELETE, LOGIN, etc)
        tabela: Nome da tabela afetada (opcional)
        registro_id: ID do registro afetado (opcional)
        detalhes: Informações adicionais (opcional)
    """
    msg = f"[AUDITORIA] {usuario} | {acao}"
    if tabela:
        msg += f" | {tabela}"
    if registro_id:
        msg += f"#{registro_id}"
    if detalhes:
        msg += f" | {detalhes}"
    logger.info(msg)


def registrar_seguranca(
    logger: logging.Logger, evento: str, usuario: str = None, detalhes: str = None
):
    """
    Registra eventos de segurança (tentativas de acesso negado, força bruta, etc).

    Args:
        logger: Logger a usar
        evento: Tipo de evento de segurança
        usuario: Usuário envolvido (opcional)
        detalhes: Informações adicionais (opcional)
    """
    msg = f"[SEGURANÇA] {evento}"
    if usuario:
        msg += f" | {usuario}"
    if detalhes:
        msg += f" | {detalhes}"
    logger.warning(msg)


def log_request_response(logger: logging.Logger):
    """
    Decorator para registrar requisições e respostas HTTP.

    Uso:
        @app.before_request
        @log_request_response(logger)
        def antes_requisicao():
            pass
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import g

            g.start_time = datetime.utcnow()
            return f(*args, **kwargs)

        return wrapper

    return decorator


def log_resposta_http(logger: logging.Logger):
    """
    Decorator para registrar resposta HTTP após processamento.
    Deve ser usado em @app.after_request.
    """

    def decorator(f):
        @wraps(f)
        def wrapper(response, *args, **kwargs):
            from flask import g, request

            # Calcular tempo de processamento
            duracao = None
            if hasattr(g, "start_time"):
                duracao = (datetime.utcnow() - g.start_time).total_seconds()

            # Evitar logar arquivo estático em debug
            if request.endpoint not in ["static"]:
                msg = f"HTTP {response.status_code} | {request.method} {request.path}"
                if duracao:
                    msg += f" | {duracao:.3f}s"

                # Nível de log baseado no status code
                if response.status_code >= 500:
                    logger.error(msg)
                elif response.status_code >= 400:
                    logger.warning(msg)
                else:
                    logger.debug(msg)

            return f(response, *args, **kwargs)

        return wrapper

    return decorator


# Logger global da aplicação
app_logger = criar_logger("estoque")

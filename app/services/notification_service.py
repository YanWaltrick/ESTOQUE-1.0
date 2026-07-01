import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app

from app.auth.security import validate_email


def _normalizar_lista_emails(valor: str) -> list[str]:
    emails = []
    for item in (valor or "").split(","):
        email = item.strip()
        if not email:
            continue
        is_valid, _ = validate_email(email)
        if is_valid:
            emails.append(email)
    return emails


def _obter_destino_webhook() -> tuple[str, str]:
    url_teams = (current_app.config.get("TEAMS_CHANNEL_WEBHOOK_URL") or "").strip()
    if url_teams:
        return url_teams, "teams"

    url_legacy = (current_app.config.get("POWER_AUTOMATE_WEBHOOK_URL") or "").strip()
    if url_legacy:
        return url_legacy, "legacy"

    return "", ""


def _obter_base_publica() -> str:
    return (current_app.config.get("APP_PUBLIC_BASE_URL") or "").strip().rstrip("/")


def _montar_url_absoluta(caminho: str | None) -> str | None:
    if not caminho:
        return None

    base_publica = _obter_base_publica()
    if not base_publica:
        return None

    return f"{base_publica}/{caminho.lstrip('/')}"


def _obter_destinatario_solicitante(chamada) -> str | None:
    usuario = getattr(chamada, "usuario", None)
    if not usuario:
        return None

    if getattr(usuario, "email", None):
        is_valid, _ = validate_email(usuario.email)
        if is_valid:
            return usuario.email.strip()

    if getattr(usuario, "username", None):
        is_valid, _ = validate_email(usuario.username)
        if is_valid:
            return usuario.username.strip()

    return None


def _obter_nome_exibicao_usuario(usuario) -> str:
    if not usuario:
        return "Não informado"

    nome = getattr(usuario, "username", None) or getattr(usuario, "email", None)
    return nome or "Não informado"


def _montar_mencoes(chamada) -> list[dict]:
    mencoes = []
    usuario = getattr(chamada, "usuario", None)

    email_solicitante = _obter_destinatario_solicitante(chamada)
    if email_solicitante:
        mencoes.append(
            {
                "text": f"<at>{_obter_nome_exibicao_usuario(usuario)}</at>",
                "mentioned": {
                    "id": email_solicitante,
                    "name": _obter_nome_exibicao_usuario(usuario),
                },
            }
        )

    return mencoes


def _montar_payload_legacy(chamada, evento: str, status_anterior: str | None = None) -> dict:
    usuario = getattr(chamada, "usuario", None)
    admins = _normalizar_lista_emails(current_app.config.get("ADMIN_EMAILS", ""))

    return {
        "origem": "estoque",
        "evento": evento,
        "enviado_em": datetime.utcnow().isoformat() + "Z",
        "chamada": {
            "id": chamada.id_chamada,
            "mensagem": chamada.mensagem,
            "status_atual": chamada.status,
            "status_anterior": status_anterior,
            "lida": chamada.lida,
            "data_criacao": chamada.data_criacao.isoformat() if chamada.data_criacao else None,
            "foto_anexo": chamada.foto_anexo,
            "foto_url": f"/static/uploads/chamadas/{chamada.foto_anexo}"
            if chamada.foto_anexo
            else None,
            "usuario": {
                "id": usuario.id if usuario else None,
                "username": usuario.username if usuario else None,
                "email": usuario.email if usuario and getattr(usuario, "email", None) else None,
                "area": usuario.area if usuario and getattr(usuario, "area", None) else None,
                "localizacao": usuario.localizacao
                if usuario and getattr(usuario, "localizacao", None)
                else None,
                "foto_perfil": usuario.foto_perfil
                if usuario and getattr(usuario, "foto_perfil", None)
                else None,
            },
        },
        "destinatarios": {
            "solicitante": _obter_destinatario_solicitante(chamada),
            "admins": admins,
            "teams": ["solicitante", "admins"],
        },
    }


def _obter_cor_tema(evento: str, status_atual: str | None = None) -> str:
    if evento == "chamada_criada":
        return "bd9a5f"

    status_normalizado = (status_atual or "").strip().lower()
    if status_normalizado == "concluida":
        return "bd9a5f"
    if status_normalizado in {"execucao", "analise"}:
        return "bd9a5f"
    return "bd9a5f"


def _obter_label_status(status_atual: str | None) -> str:
    status_normalizado = (status_atual or "").strip().lower()
    if status_normalizado == "concluida":
        return "Concluída"
    if status_normalizado == "execucao":
        return "Em execução"
    if status_normalizado == "analise":
        return "Em análise"
    if status_normalizado == "lida":
        return "Lida"
    if status_normalizado == "nova":
        return "Nova"
    return status_atual or "Não informado"


def _obter_cor_status(status_atual: str | None) -> str:
    status_normalizado = (status_atual or "").strip().lower()
    if status_normalizado == "concluida":
        return "good"
    if status_normalizado in {"execucao", "analise"}:
        return "attention"
    if status_normalizado == "nova":
        return "warning"
    return "default"


def montar_payload_notificacao_chamada(
    chamada, evento: str, status_anterior: str | None = None, modo: str | None = None
) -> dict:
    if modo == "legacy":
        return _montar_payload_legacy(chamada, evento, status_anterior=status_anterior)

    usuario = getattr(chamada, "usuario", None)
    nome_usuario = _obter_nome_exibicao_usuario(usuario)

    status_atual = (chamada.status or "").strip() or "não informado"
    evento_titulo = "Chamado atualizado"
    mencoes = _montar_mencoes(chamada)
    mencoes_texto = " ".join(item["text"] for item in mencoes).strip()
    data_texto = chamada.data_criacao.strftime("%d/%m/%Y %H:%M") if chamada.data_criacao else "N/A"
    status_label = _obter_label_status(status_atual)

    body = [
        {
            "type": "Container",
            "style": "emphasis",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "SOMA ASSET | SISTEMATI",
                    "size": "Small",
                    "weight": "Bolder",
                    "color": "dark",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": evento_titulo,
                    "size": "Large",
                    "weight": "Bolder",
                    "color": "dark",
                    "wrap": True,
                    "spacing": "Small",
                },
                {
                    "type": "TextBlock",
                    "text": f"Chamado #{chamada.id_chamada}",
                    "size": "Medium",
                    "weight": "Bolder",
                    "color": "dark",
                    "wrap": True,
                    "spacing": "Small",
                },
            ],
            "spacing": "None",
            "padding": "Default",
        },
        {
            "type": "Container",
            "style": "default",
            "items": [
                {
                    "type": "TextBlock",
                    "text": mencoes_texto or f"@{nome_usuario}",
                    "wrap": True,
                    "weight": "Bolder",
                    "color": "dark",
                },
                {
                    "type": "TextBlock",
                    "text": chamada.mensagem or "Sem detalhes informados",
                    "wrap": True,
                    "spacing": "Small",
                    "color": "dark",
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Nº chamado", "value": f"#{chamada.id_chamada}"},
                        {"title": "Solicitante", "value": nome_usuario},
                        {"title": "Status atual", "value": status_label},
                        {"title": "Data", "value": data_texto},
                    ],
                    "spacing": "Medium",
                },
                {
                    "type": "TextBlock",
                    "text": "SOMA ASSET",
                    "spacing": "Medium",
                    "separator": True,
                    "weight": "Bolder",
                    "color": "dark",
                    "size": "Small",
                },
            ],
            "spacing": "Medium",
            "padding": "Default",
        },
    ]

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.5",
                    "body": body,
                    "msteams": {
                        "width": "full",
                        "entities": mencoes,
                    },
                },
            }
        ],
    }


def enviar_notificacao_chamada(
    chamada, evento: str, status_anterior: str | None = None
) -> tuple[bool, str]:
    url_webhook, modo = _obter_destino_webhook()
    if not url_webhook:
        return True, ""

    payload = montar_payload_notificacao_chamada(
        chamada, evento, status_anterior=status_anterior, modo=modo
    )
    timeout = current_app.config.get("POWER_AUTOMATE_TIMEOUT_SECONDS", 10)

    try:
        dados = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        requisicao = Request(
            url_webhook,
            data=dados,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urlopen(requisicao, timeout=timeout) as resposta:
            resposta.read()
        return True, ""
    except HTTPError as e:
        mensagem = f"HTTP {e.code}: {e.reason}"
        current_app.logger.warning(
            "Falha ao enviar notificação para webhook do Teams: %s", mensagem
        )
        return False, mensagem
    except URLError as e:
        mensagem = str(e.reason or e)
        current_app.logger.warning(
            "Falha ao enviar notificação para webhook do Teams: %s", mensagem
        )
        return False, mensagem
    except Exception as e:
        mensagem = str(e)
        current_app.logger.warning(
            "Falha ao enviar notificação para webhook do Teams: %s", mensagem
        )
        return False, mensagem

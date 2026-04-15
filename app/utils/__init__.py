from flask_login import current_user
from app.database import db
from app.models import Historico

def registrar_evento(tipo_evento, descricao, usuario_responsavel=None, detalhes=None):
    """Registra um evento no histórico do sistema"""
    try:
        if usuario_responsavel is None and current_user.is_authenticated:
            usuario_responsavel = current_user.username

        evento = Historico(
            tipo_evento=tipo_evento,
            descricao=descricao,
            usuario_responsavel=usuario_responsavel,
            detalhes=detalhes
        )
        db.session.add(evento)
        db.session.commit()
    except Exception as e:
        print(f"Erro ao registrar evento no histórico: {e}")
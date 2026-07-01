import io
import os
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.database import db
from app.models import DocumentoArquivo, DocumentoUsuario, User
from app.utils import registrar_evento

main_bp = Blueprint("main", __name__)

EXTENSOES_PERMITIDAS_DOCUMENTOS = {"pdf", "doc", "docx", "xls", "xlsx", "txt", "jpg", "jpeg", "png"}
TAMANHO_MAXIMO_DOCUMENTO = 10 * 1024 * 1024  # 10 MB


def _pasta_documentos():
    pasta = os.path.join(current_app.root_path, "..", "static", "uploads", "documentos")
    pasta = os.path.abspath(pasta)
    os.makedirs(pasta, exist_ok=True)
    return pasta


@main_bp.route("/")
@login_required
def index():
    """Página principal do dashboard"""
    return render_template("index.html")


@main_bp.route("/admin")
@login_required
def admin():
    """Página de administração de usuários"""
    if not current_user.is_admin:
        return redirect(url_for("main.index"))
    return render_template("admin.html")


@main_bp.route("/documentos")
@login_required
def documentos():
    """Tela de documentos empresariais."""
    usuarios = []
    if current_user.is_admin:
        usuarios = User.query.filter_by(ativo=True).order_by(User.username.asc()).all()

    if current_user.is_admin:
        docs = DocumentoUsuario.query.order_by(DocumentoUsuario.data_criacao.desc()).all()
    else:
        docs = (
            DocumentoUsuario.query.filter_by(id_usuario=current_user.id)
            .order_by(DocumentoUsuario.data_criacao.desc())
            .all()
        )

    return render_template(
        "documentos.html",
        documentos=docs,
        usuarios=usuarios,
        allowed_extensions=sorted(EXTENSOES_PERMITIDAS_DOCUMENTOS),
        max_upload_mb=int(TAMANHO_MAXIMO_DOCUMENTO / (1024 * 1024)),
    )


@main_bp.route("/documentos/upload", methods=["POST"])
@login_required
def upload_documento():
    """Upload de documento empresarial para um usuário selecionado."""
    if "arquivo" not in request.files:
        flash("Nenhum arquivo foi enviado.", "error")
        return redirect(url_for("main.documentos"))

    arquivo = request.files["arquivo"]
    nome_documento = request.form.get("nome_documento", "").strip()
    descricao = request.form.get("descricao", "").strip() or None
    id_usuario_form = request.form.get("id_usuario", "").strip()

    if current_user.is_admin:
        if not id_usuario_form.isdigit():
            flash("Selecione um usuário válido para receber o documento.", "error")
            return redirect(url_for("main.documentos"))

        usuario_destino = User.query.filter_by(id=int(id_usuario_form), ativo=True).first()
        if not usuario_destino:
            flash("Usuário selecionado não encontrado ou está inativo.", "error")
            return redirect(url_for("main.documentos"))
    else:
        usuario_destino = current_user

    if arquivo.filename == "":
        flash("Selecione um arquivo para enviar.", "error")
        return redirect(url_for("main.documentos"))

    if not nome_documento:
        flash("Informe o nome do documento.", "error")
        return redirect(url_for("main.documentos"))

    if "." not in arquivo.filename:
        flash("Arquivo sem extensão válida.", "error")
        return redirect(url_for("main.documentos"))

    extensao = arquivo.filename.rsplit(".", 1)[1].lower()
    if extensao not in EXTENSOES_PERMITIDAS_DOCUMENTOS:
        flash("Tipo de arquivo não permitido.", "error")
        return redirect(url_for("main.documentos"))

    arquivo.seek(0, os.SEEK_END)
    tamanho = arquivo.tell()
    arquivo.seek(0)

    if tamanho <= 0:
        flash("Arquivo vazio não é permitido.", "error")
        return redirect(url_for("main.documentos"))

    if tamanho > TAMANHO_MAXIMO_DOCUMENTO:
        flash(
            f"Arquivo muito grande. Limite: {int(TAMANHO_MAXIMO_DOCUMENTO / (1024 * 1024))}MB.",
            "error",
        )
        return redirect(url_for("main.documentos"))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo_seguro = secure_filename(f"{usuario_destino.id}_{timestamp}_{arquivo.filename}")
    caminho_arquivo = os.path.join(_pasta_documentos(), nome_arquivo_seguro)

    try:
        arquivo.save(caminho_arquivo)

        # Espelhar no banco para sobreviver ao disco efêmero do App Service
        # (ver DocumentoArquivo.salvar_do_arquivo). Falha é não-crítica.
        DocumentoArquivo.salvar_do_arquivo(
            caminho_arquivo, filename=nome_arquivo_seguro, tamanho=tamanho
        )

        novo_documento = DocumentoUsuario(
            id_usuario=usuario_destino.id,
            nome_documento=nome_documento,
            arquivo=nome_arquivo_seguro,
            tipo_arquivo=extensao,
            tamanho_arquivo=tamanho,
            usuario_enviador=current_user.username,
            descricao=descricao,
        )
        db.session.add(novo_documento)
        db.session.commit()

        registrar_evento(
            tipo_evento="documento_empresarial_enviado",
            descricao=f'Documento "{nome_documento}" enviado por "{current_user.username}" para "{usuario_destino.username}"',
            usuario_responsavel=current_user.username,
            detalhes=f"arquivo={nome_arquivo_seguro}; tamanho={tamanho}",
        )
        flash("Documento enviado com sucesso.", "success")
    except Exception:
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)
        db.session.rollback()
        flash("Não foi possível salvar o documento.", "error")

    return redirect(url_for("main.documentos"))


@main_bp.route("/documentos/<int:documento_id>/download")
@login_required
def download_documento(documento_id):
    """Download de documento empresarial."""
    documento = DocumentoUsuario.query.get_or_404(documento_id)

    if not current_user.is_admin and documento.id_usuario != current_user.id:
        flash("Você não tem permissão para baixar este documento.", "error")
        return redirect(url_for("main.documentos"))

    caminho_arquivo = os.path.join(_pasta_documentos(), documento.arquivo)
    if not os.path.exists(caminho_arquivo):
        # tentar recuperar do banco
        blob = DocumentoArquivo.query.filter_by(filename=documento.arquivo).first()
        if not blob:
            flash("Arquivo não encontrado no servidor.", "error")
            return redirect(url_for("main.documentos"))

        nome_download = f"{documento.nome_documento}.{documento.tipo_arquivo}"
        bio = io.BytesIO(blob.content)
        bio.seek(0)
        return send_file(
            bio,
            as_attachment=True,
            download_name=nome_download,
            mimetype=blob.mime_type or "application/octet-stream",
        )

    nome_download = f"{documento.nome_documento}.{documento.tipo_arquivo}"
    return send_file(caminho_arquivo, as_attachment=True, download_name=nome_download)


@main_bp.route("/documentos/<int:documento_id>/excluir", methods=["POST"])
@login_required
def excluir_documento(documento_id):
    """Exclusão de documento empresarial."""
    documento = DocumentoUsuario.query.get_or_404(documento_id)

    if not current_user.is_admin and documento.id_usuario != current_user.id:
        flash("Você não tem permissão para excluir este documento.", "error")
        return redirect(url_for("main.documentos"))

    caminho_arquivo = os.path.join(_pasta_documentos(), documento.arquivo)
    try:
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)

        # remover também do banco de blobs, se existir
        try:
            DocumentoArquivo.query.filter_by(filename=documento.arquivo).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()

        nome_documento = documento.nome_documento

        db.session.delete(documento)
        db.session.commit()

        registrar_evento(
            tipo_evento="documento_empresarial_excluido",
            descricao=f'Documento "{nome_documento}" excluído por "{current_user.username}"',
            usuario_responsavel=current_user.username,
        )
        flash("Documento excluído com sucesso.", "success")
    except Exception:
        db.session.rollback()
        flash("Não foi possível excluir o documento.", "error")

    return redirect(url_for("main.documentos"))

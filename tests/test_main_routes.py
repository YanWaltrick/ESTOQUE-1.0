"""Testes das rotas de `app/routes/main.py`.

Cobrem dashboard/index, controle de acesso a `/admin`, e o fluxo de documentos
(listar, upload, download e exclusão).
"""

from io import BytesIO

from app.models import DocumentoUsuario

# --- Index / admin ----------------------------------------------------------


def test_index_autenticado(auth_client):
    resp = auth_client.get("/")
    assert resp.status_code == 200


def test_index_anonimo_redireciona(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302


def test_admin_como_admin(auth_client):
    resp = auth_client.get("/admin")
    assert resp.status_code == 200


def test_admin_como_usuario_redireciona(user_client):
    resp = user_client.get("/admin", follow_redirects=False)
    assert resp.status_code == 302


# --- Documentos -------------------------------------------------------------


def test_documentos_admin(auth_client):
    resp = auth_client.get("/documentos")
    assert resp.status_code == 200


def test_documentos_usuario_comum(user_client):
    resp = user_client.get("/documentos")
    assert resp.status_code == 200


def _upload(client, id_usuario, nome="Documento Main", filename="doc.pdf"):
    data = {
        "arquivo": (BytesIO(b"conteudo do documento de teste"), filename),
        "nome_documento": nome,
        "descricao": "descricao",
        "id_usuario": str(id_usuario),
    }
    return client.post(
        "/documentos/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )


def test_upload_documento_admin(auth_client, db_session, criar_usuario):
    alvo = criar_usuario(username="main_doc_alvo")
    resp = _upload(auth_client, alvo.id)
    assert resp.status_code == 302
    assert DocumentoUsuario.query.filter_by(id_usuario=alvo.id).count() >= 1


def test_upload_documento_sem_arquivo(auth_client, db_session, criar_usuario):
    alvo = criar_usuario(username="main_sem_arquivo")
    resp = auth_client.post(
        "/documentos/upload",
        data={"nome_documento": "X", "id_usuario": str(alvo.id)},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code == 302  # redireciona com flash de erro


def test_download_documento(auth_client, db_session, criar_usuario):
    alvo = criar_usuario(username="main_download")
    _upload(auth_client, alvo.id, nome="Para Download")
    doc = DocumentoUsuario.query.filter_by(id_usuario=alvo.id).first()
    resp = auth_client.get(f"/documentos/{doc.id_documento}/download")
    assert resp.status_code == 200


def test_excluir_documento(auth_client, db_session, criar_usuario):
    alvo = criar_usuario(username="main_excluir")
    _upload(auth_client, alvo.id, nome="Para Excluir")
    doc = DocumentoUsuario.query.filter_by(id_usuario=alvo.id).first()
    resp = auth_client.post(f"/documentos/{doc.id_documento}/excluir", follow_redirects=False)
    assert resp.status_code == 302
    assert DocumentoUsuario.query.get(doc.id_documento) is None


def test_download_documento_inexistente(auth_client):
    resp = auth_client.get("/documentos/999999/download")
    assert resp.status_code == 404

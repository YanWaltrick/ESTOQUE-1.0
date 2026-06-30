"""Testes das rotas administrativas de `app/routes/admin.py` (prefixo `/admin`).

Todo o blueprint exige login + role admin (`before_request`). Usam
`auth_client` (admin) e `user_client` (comum). Algumas rotas escrevem PDFs em
`static/uploads/` — efeito colateral aceito nos testes.
"""

import os
from io import BytesIO

import pytest

from app.models import DocumentoArquivo, DocumentoUsuario, TermoEntrega, User


def _pasta_documentos_teste():
    """Pasta física onde as rotas gravam os documentos (raiz do projeto)."""
    raiz = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(raiz, "static", "uploads", "documentos")

# O fixture `admin_user` vem do `conftest.py` (compartilhado com test_api.py).


# --- RBAC -------------------------------------------------------------------


def test_rbac_usuario_comum_barrado(user_client):
    resp = user_client.get("/admin/users")
    assert resp.status_code == 403


def test_rbac_anonimo_redireciona(client):
    resp = client.get("/admin/users", follow_redirects=False)
    assert resp.status_code == 302


# --- Listagens / páginas (render_template) ----------------------------------


def test_listar_usuarios(auth_client):
    resp = auth_client.get("/admin/users")
    assert resp.status_code == 200


def test_listar_usuarios_com_filtros(auth_client):
    resp = auth_client.get("/admin/users?q=admin&tipo=CLT&page=1")
    assert resp.status_code == 200


# NOTA: as rotas `/admin/dashboard` e `/admin/audit-log` são órfãs — seus
# templates (`admin/dashboard.html`, `admin/audit_log.html`) não existem no
# projeto e nenhum link aponta para elas (o dashboard real é servido por
# `main.py:/admin`). Acessá-las levanta `TemplateNotFound` (a view roda a query,
# mas falha no render). Os testes abaixo documentam esse estado conhecido.
# Ver docs/testes/ROADMAP.md.


def test_dashboard_rota_orfa_sem_template(auth_client):
    from jinja2.exceptions import TemplateNotFound

    with pytest.raises(TemplateNotFound):
        auth_client.get("/admin/dashboard")


def test_audit_log_rota_orfa_sem_template(auth_client):
    from jinja2.exceptions import TemplateNotFound

    with pytest.raises(TemplateNotFound):
        auth_client.get("/admin/audit-log")


def test_usuarios_pagina(auth_client):
    resp = auth_client.get("/admin/usuarios")
    assert resp.status_code == 200


def test_form_criar_usuario(auth_client):
    resp = auth_client.get("/admin/users/create")
    assert resp.status_code == 200


def test_form_editar_usuario(auth_client, criar_usuario):
    alvo = criar_usuario(username="edit_form")
    resp = auth_client.get(f"/admin/users/{alvo.id}/edit")
    assert resp.status_code == 200


# --- Criar / editar usuário (POST -> redirect, verifica no banco) -----------


def test_criar_usuario_post(auth_client, db_session):
    resp = auth_client.post(
        "/admin/users/create",
        data={"username": "criado_admin", "password": "Senha123", "role": "usuario"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert User.query.filter_by(username="criado_admin").first() is not None


def test_editar_usuario_post(auth_client, db_session, criar_usuario):
    alvo = criar_usuario(username="edit_post")
    resp = auth_client.post(
        f"/admin/users/{alvo.id}/edit",
        data={"username": "edit_post", "area": "Financeiro", "role": "usuario"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    db_session.refresh(alvo)
    assert alvo.area == "Financeiro"


# --- Deletar / reset / bloqueio (JSON) --------------------------------------


def test_deletar_usuario_proprio_negado(auth_client, admin_user):
    resp = auth_client.post(f"/admin/users/{admin_user.id}/delete")
    assert resp.status_code == 403
    assert resp.get_json()["success"] is False


def test_deletar_usuario_comum(auth_client, criar_usuario):
    alvo = criar_usuario(username="del_comum")
    resp = auth_client.post(f"/admin/users/{alvo.id}/delete")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_resetar_senha(auth_client, criar_usuario):
    alvo = criar_usuario(username="reset_admin")
    resp = auth_client.post(
        f"/admin/users/{alvo.id}/reset-password", data={"nova_senha": "NovaSenha1"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_resetar_senha_invalida(auth_client, criar_usuario):
    alvo = criar_usuario(username="reset_invalido")
    resp = auth_client.post(
        f"/admin/users/{alvo.id}/reset-password", data={"nova_senha": "123"}
    )
    assert resp.status_code == 400


def test_toggle_bloqueio_proprio_negado(auth_client, admin_user):
    resp = auth_client.post(f"/admin/users/{admin_user.id}/toggle-block")
    assert resp.status_code == 403


def test_toggle_bloqueio_outro(auth_client, criar_usuario):
    alvo = criar_usuario(username="block_alvo")
    resp = auth_client.post(f"/admin/users/{alvo.id}/toggle-block")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


# --- Documentos -------------------------------------------------------------


def test_upload_documento(auth_client, criar_usuario):
    alvo = criar_usuario(username="doc_alvo")
    data = {
        "arquivo": (BytesIO(b"conteudo de teste do pdf"), "documento.pdf"),
        "nome": "Documento de Teste",
        "descricao": "desc",
    }
    resp = auth_client.post(
        f"/admin/usuarios/{alvo.id}/documentos/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_listar_documentos_usuario(auth_client, criar_usuario):
    alvo = criar_usuario(username="doc_lista")
    resp = auth_client.get(f"/admin/usuarios/{alvo.id}/documentos")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


# --- Itens recebidos --------------------------------------------------------


def test_itens_recebidos_fluxo_completo(auth_client, criar_usuario):
    alvo = criar_usuario(username="itens_alvo")

    # Listar (vazio)
    resp = auth_client.get(f"/admin/usuarios/{alvo.id}/itens-recebidos")
    assert resp.status_code == 200

    # Adicionar
    resp = auth_client.post(
        f"/admin/usuarios/{alvo.id}/itens-recebidos/adicionar",
        data={"descricao": "Notebook", "tipo": "entrada"},
    )
    assert resp.status_code == 200
    item_id = resp.get_json()["item"]["id"]

    # Editar (PUT json)
    resp = auth_client.put(
        f"/admin/usuarios/itens-recebidos/{item_id}/editar",
        json={"descricao": "Notebook Dell", "tipo": "posteriormente"},
    )
    assert resp.status_code == 200

    # Deletar (DELETE)
    resp = auth_client.delete(f"/admin/usuarios/itens-recebidos/{item_id}/deletar")
    assert resp.status_code == 200


def test_adicionar_item_sem_descricao(auth_client, criar_usuario):
    alvo = criar_usuario(username="item_invalido")
    resp = auth_client.post(
        f"/admin/usuarios/{alvo.id}/itens-recebidos/adicionar",
        data={"descricao": "", "tipo": "entrada"},
    )
    assert resp.status_code == 400


def test_relatorio_itens_pdf(auth_client, criar_usuario):
    alvo = criar_usuario(username="rel_itens")
    auth_client.post(
        f"/admin/usuarios/{alvo.id}/itens-recebidos/adicionar",
        data={"descricao": "Mouse", "tipo": "entrada"},
    )
    resp = auth_client.get(f"/admin/usuarios/{alvo.id}/itens-recebidos/relatorio")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"


# --- Termo de entrega -------------------------------------------------------


def test_listar_termo_entrega(auth_client, criar_usuario):
    alvo = criar_usuario(username="termo_lista")
    resp = auth_client.get(f"/admin/usuarios/{alvo.id}/termo-entrega")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_atualizar_termo_entrega(auth_client, db_session, criar_usuario):
    alvo = criar_usuario(username="termo_upd", tipo_contrato="CLT")
    resp = auth_client.post(
        f"/admin/usuarios/{alvo.id}/termo-entrega/atualizar",
        data={"empresa": "ACME LTDA", "cnpj": "12.345.678/0001-90", "cargo_funcao": "Analista"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_equipamento_adicionar_e_deletar(auth_client, criar_usuario):
    alvo = criar_usuario(username="equip_alvo")
    # Adiciona equipamento (cria o termo se não existir)
    resp = auth_client.post(
        f"/admin/usuarios/{alvo.id}/termo-entrega/equipamentos/adicionar",
        data={"descricao": "Notebook", "marca": "Dell", "modelo": "5440"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    eq_id = resp.get_json()["equipamento"]["id"]

    # Deleta o equipamento
    resp = auth_client.delete(
        f"/admin/usuarios/{alvo.id}/termo-entrega/equipamentos/{eq_id}/deletar"
    )
    assert resp.status_code == 200


def test_assinar_termo_descontinuado(auth_client, criar_usuario):
    alvo = criar_usuario(username="assina_alvo")
    resp = auth_client.post(f"/admin/usuarios/{alvo.id}/termo-entrega/assinar")
    assert resp.get_json()["success"] is False


def test_exportar_termo_pdf(auth_client, db_session, criar_usuario):
    alvo = criar_usuario(username="export_alvo", tipo_contrato="CLT")
    # Garante termo com equipamento
    auth_client.post(
        f"/admin/usuarios/{alvo.id}/termo-entrega/equipamentos/adicionar",
        data={"descricao": "Notebook", "marca": "Dell"},
        content_type="multipart/form-data",
    )
    resp = auth_client.post(
        f"/admin/usuarios/{alvo.id}/termo-entrega/exportar", json={}
    )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_exportar_termo_sem_termo(auth_client, criar_usuario):
    alvo = criar_usuario(username="export_sem_termo")
    resp = auth_client.post(
        f"/admin/usuarios/{alvo.id}/termo-entrega/exportar", json={}
    )
    assert resp.status_code == 404


# --- Ramos adicionais -------------------------------------------------------


def test_criar_usuario_username_invalido_nao_cria(auth_client, db_session):
    auth_client.post(
        "/admin/users/create",
        data={"username": "ab", "password": "Senha123"},
        follow_redirects=False,
    )
    assert User.query.filter_by(username="ab").first() is None


def test_upload_foto_usuario(auth_client, criar_usuario):
    alvo = criar_usuario(username="foto_alvo")
    data = {"foto_perfil": (BytesIO(b"\x89PNG\r\n\x1a\nfoto"), "avatar.png")}
    resp = auth_client.post(
        f"/admin/users/{alvo.id}/upload-photo",
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_visualizar_e_download_documento(auth_client, db_session, criar_usuario):
    alvo = criar_usuario(username="doc_visualizar")
    data = {
        "arquivo": (BytesIO(b"conteudo pdf"), "arquivo.pdf"),
        "nome": "Doc Visualizar",
    }
    auth_client.post(
        f"/admin/usuarios/{alvo.id}/documentos/upload",
        data=data,
        content_type="multipart/form-data",
    )
    doc = DocumentoUsuario.query.filter_by(id_usuario=alvo.id).first()

    resp_view = auth_client.get(f"/admin/usuarios/documentos/{doc.id_documento}/visualizar")
    assert resp_view.status_code == 200

    resp_dl = auth_client.get(f"/admin/usuarios/documentos/{doc.id_documento}/download")
    assert resp_dl.status_code == 200


def test_adicionar_equipamento_sem_descricao(auth_client, criar_usuario):
    alvo = criar_usuario(username="equip_invalido")
    resp = auth_client.post(
        f"/admin/usuarios/{alvo.id}/termo-entrega/equipamentos/adicionar",
        data={"descricao": ""},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_editar_item_inexistente(auth_client, db_session):
    resp = auth_client.put(
        "/admin/usuarios/itens-recebidos/999999/editar",
        json={"descricao": "X"},
    )
    assert resp.status_code == 404


def test_deletar_item_inexistente(auth_client, db_session):
    resp = auth_client.delete("/admin/usuarios/itens-recebidos/999999/deletar")
    assert resp.status_code == 404


def test_criar_usuario_pj_via_form(auth_client, db_session):
    resp = auth_client.post(
        "/admin/users/create",
        data={
            "username": "pj_form",
            "password": "Senha123",
            "role": "usuario",
            "tipo_contrato": "PJ",
            "pj_contratante": "Contratante SA",
            "pj_contratante_cnpj": "98.765.432/0001-10",
            "pj_contratada": "Contratada ME",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    user = User.query.filter_by(username="pj_form").first()
    assert user is not None
    assert user.tipo_contrato == "PJ"
    assert TermoEntrega.query.filter_by(id_usuario=user.id).first() is not None


def test_atualizar_termo_com_datas(auth_client, db_session, criar_usuario):
    alvo = criar_usuario(username="termo_datas", tipo_contrato="CLT")
    resp = auth_client.post(
        f"/admin/usuarios/{alvo.id}/termo-entrega/atualizar",
        data={
            "empresa": "ACME",
            "cargo_funcao": "Analista",
            "data_admissao": "2024-01-15",
            "observacoes": "Observação de teste",
        },
    )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_editar_usuario_propria_conta_bloqueado(auth_client, admin_user):
    # Admin tentando editar a própria conta via /edit é barrado (redireciona).
    resp = auth_client.post(
        f"/admin/users/{admin_user.id}/edit",
        data={"username": "admin", "area": "NovaArea"},
        follow_redirects=False,
    )
    assert resp.status_code == 302


# --- Persistência de documentos no banco (resiliência ao disco efêmero) ------


def test_upload_documento_persiste_blob(auth_client, db_session, criar_usuario):
    """O upload do admin deve espelhar o arquivo em DocumentoArquivo (não só em disco)."""
    alvo = criar_usuario(username="doc_blob")
    conteudo = b"conteudo de teste do pdf"
    auth_client.post(
        f"/admin/usuarios/{alvo.id}/documentos/upload",
        data={"arquivo": (BytesIO(conteudo), "documento.pdf"), "nome": "Doc Blob"},
        content_type="multipart/form-data",
    )
    doc = DocumentoUsuario.query.filter_by(id_usuario=alvo.id).first()
    blob = DocumentoArquivo.query.filter_by(filename=doc.arquivo).first()
    assert blob is not None, "upload do admin não gravou o blob no banco"
    assert blob.content == conteudo
    assert blob.size == len(conteudo)


def test_visualizar_e_download_caem_para_o_banco_sem_disco(auth_client, db_session, criar_usuario):
    """Sem o arquivo no disco (disco efêmero), as rotas servem o conteúdo do banco."""
    alvo = criar_usuario(username="doc_fallback")
    conteudo = b"conteudo somente no banco"
    auth_client.post(
        f"/admin/usuarios/{alvo.id}/documentos/upload",
        data={"arquivo": (BytesIO(conteudo), "fallback.pdf"), "nome": "Doc Fallback"},
        content_type="multipart/form-data",
    )
    doc = DocumentoUsuario.query.filter_by(id_usuario=alvo.id).first()

    # Simula a reciclagem do disco efêmero: remove o arquivo, deixa só o blob.
    caminho = os.path.join(_pasta_documentos_teste(), doc.arquivo)
    if os.path.exists(caminho):
        os.remove(caminho)

    resp_view = auth_client.get(f"/admin/usuarios/documentos/{doc.id_documento}/visualizar")
    assert resp_view.status_code == 200
    assert resp_view.data == conteudo

    resp_dl = auth_client.get(f"/admin/usuarios/documentos/{doc.id_documento}/download")
    assert resp_dl.status_code == 200
    assert resp_dl.data == conteudo


def test_exportar_termo_persiste_blob_com_upsert(auth_client, db_session, criar_usuario):
    """O termo gerado deve ser espelhado no banco, e regerar não deve duplicar o blob."""
    alvo = criar_usuario(username="termo_blob", tipo_contrato="CLT")
    auth_client.post(
        f"/admin/usuarios/{alvo.id}/termo-entrega/equipamentos/adicionar",
        data={"descricao": "Notebook", "marca": "Dell"},
        content_type="multipart/form-data",
    )
    auth_client.post(f"/admin/usuarios/{alvo.id}/termo-entrega/exportar", json={})

    nome_arquivo = f"termo_{alvo.id}.pdf"
    blobs = DocumentoArquivo.query.filter_by(filename=nome_arquivo).all()
    assert len(blobs) == 1, "geração do termo não gravou exatamente um blob no banco"
    assert blobs[0].size > 0
    assert blobs[0].mime_type == "application/pdf"

    # Regenera o termo (mesmo nome fixo): o upsert por filename substitui, não duplica.
    auth_client.post(f"/admin/usuarios/{alvo.id}/termo-entrega/exportar", json={})
    blobs = DocumentoArquivo.query.filter_by(filename=nome_arquivo).all()
    assert len(blobs) == 1, "regerar o termo duplicou o blob em vez de fazer upsert"


def test_leitura_ignora_arquivo_vazio_e_cai_para_o_banco(auth_client, db_session, criar_usuario):
    """Arquivo de 0 byte no disco (disco efêmero corrompido) é ignorado em favor do blob."""
    alvo = criar_usuario(username="doc_zero")
    conteudo = b"conteudo integro no banco"
    auth_client.post(
        f"/admin/usuarios/{alvo.id}/documentos/upload",
        data={"arquivo": (BytesIO(conteudo), "zero.pdf"), "nome": "Doc Zero"},
        content_type="multipart/form-data",
    )
    doc = DocumentoUsuario.query.filter_by(id_usuario=alvo.id).first()

    # Trunca o arquivo no disco para 0 byte, simulando reciclagem parcial do disco.
    caminho = os.path.join(_pasta_documentos_teste(), doc.arquivo)
    open(caminho, "wb").close()
    assert os.path.getsize(caminho) == 0

    resp_view = auth_client.get(f"/admin/usuarios/documentos/{doc.id_documento}/visualizar")
    assert resp_view.status_code == 200
    assert resp_view.data == conteudo

    resp_dl = auth_client.get(f"/admin/usuarios/documentos/{doc.id_documento}/download")
    assert resp_dl.status_code == 200
    assert resp_dl.data == conteudo


@pytest.mark.parametrize("acao", ["visualizar", "download"])
def test_erro_na_leitura_retorna_json_sem_vazar(auth_client, db_session, criar_usuario, monkeypatch, acao):
    """Erro inesperado na leitura vira JSON genérico (não HTML) e não vaza str(e)."""
    import app.routes.admin as admin_module

    alvo = criar_usuario(username=f"doc_erro_{acao}")
    auth_client.post(
        f"/admin/usuarios/{alvo.id}/documentos/upload",
        data={"arquivo": (BytesIO(b"x"), "erro.pdf"), "nome": "Doc Erro"},
        content_type="multipart/form-data",
    )
    doc = DocumentoUsuario.query.filter_by(id_usuario=alvo.id).first()

    segredo = "DETALHE_INTERNO_SECRETO"

    def explode(*args, **kwargs):
        raise RuntimeError(segredo)

    monkeypatch.setattr(admin_module, "_servir_documento", explode)

    resp = auth_client.get(f"/admin/usuarios/documentos/{doc.id_documento}/{acao}")
    assert resp.status_code == 500
    assert resp.is_json, "erro deveria retornar JSON, não HTML 500 padrão do Flask"
    corpo = resp.get_data(as_text=True)
    assert segredo not in corpo, "a mensagem de erro vazou detalhes internos (str(e))"
    assert resp.get_json()["success"] is False


def test_preview_infere_mimetype_quando_blob_e_generico(auth_client, db_session, criar_usuario):
    """Blob legado com mime genérico é servido com o Content-Type inferido pela extensão."""
    alvo = criar_usuario(username="doc_mime")
    nome_arquivo = f"{alvo.id}_mime_teste.pdf"
    # Documento + blob com mime_type genérico (cenário de migração legada), sem disco.
    doc = DocumentoUsuario(
        id_usuario=alvo.id,
        nome_documento="Doc Mime",
        arquivo=nome_arquivo,
        tipo_arquivo="pdf",
        tamanho_arquivo=4,
        usuario_enviador="admin",
    )
    db_session.add(doc)
    db_session.add(
        DocumentoArquivo(
            filename=nome_arquivo,
            content=b"%PDF",
            mime_type="application/octet-stream",
            size=4,
        )
    )
    db_session.commit()

    resp = auth_client.get(f"/admin/usuarios/documentos/{doc.id_documento}/visualizar")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"


def test_download_nao_renomeia_pdf_nao_relacionado(auth_client, db_session, criar_usuario):
    """PDF cujo nome só contém 'termo'/'aditivo' como substring mantém o próprio nome."""
    alvo = criar_usuario(username="doc_garantia")
    auth_client.post(
        f"/admin/usuarios/{alvo.id}/documentos/upload",
        data={"arquivo": (BytesIO(b"conteudo"), "garantia.pdf"), "nome": "Termo de garantia"},
        content_type="multipart/form-data",
    )
    doc = DocumentoUsuario.query.filter_by(id_usuario=alvo.id).first()

    resp = auth_client.get(f"/admin/usuarios/documentos/{doc.id_documento}/download")
    assert resp.status_code == 200
    # Não deve ser renomeado para "Termo de responsabilidade de ...".
    assert "responsabilidade" not in resp.headers.get("Content-Disposition", "").lower()
    assert "Termo de garantia.pdf" in resp.headers.get("Content-Disposition", "")

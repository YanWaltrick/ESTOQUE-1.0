"""Testes das rotas administrativas de `app/routes/admin.py` (prefixo `/admin`).

Todo o blueprint exige login + role admin (`before_request`). Usam
`auth_client` (admin) e `user_client` (comum). Algumas rotas escrevem PDFs em
`static/uploads/` — efeito colateral aceito nos testes.
"""

from io import BytesIO

import pytest

from app.models import DocumentoUsuario, TermoEntrega, User

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

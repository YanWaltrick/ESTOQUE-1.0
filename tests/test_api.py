"""Testes das rotas JSON de `app/routes/api.py` (blueprint `/api`).

Usam `auth_client` (admin) e `user_client` (usuário comum) para exercitar os
endpoints e o RBAC. Produtos/chamadas são criados pela própria API para manter
a consistência com a instância de serviço usada pelas views.
"""

# O fixture `admin_user` vem do `conftest.py` (compartilhado com test_admin.py).


# --- Produtos: CRUD ---------------------------------------------------------


def _criar_produto(client, id_produto="API1", **extra):
    payload = {
        "id": id_produto,
        "nome": "Produto API",
        "categoria": "Cat",
        "preco": 10.0,
        "quantidade": 5,
        "minimo": 2,
        "localizacao": "A1",
    }
    payload.update(extra)
    return client.post("/api/produtos", json=payload)


def test_criar_produto_admin(auth_client):
    resp = _criar_produto(auth_client, "PROD_OK")
    assert resp.status_code == 201
    assert "sucesso" in resp.get_json()["mensagem"]


def test_criar_produto_invalido(auth_client):
    resp = auth_client.post("/api/produtos", json={"id": "", "nome": "", "categoria": ""})
    assert resp.status_code == 400


def test_criar_produto_negado_para_usuario(user_client):
    resp = _criar_produto(user_client, "PROD_NEG")
    assert resp.status_code == 403


def test_listar_produtos(auth_client):
    _criar_produto(auth_client, "PROD_LIST")
    resp = auth_client.get("/api/produtos")
    assert resp.status_code == 200
    ids = {p["id"] for p in resp.get_json()}
    assert "PROD_LIST" in ids


def test_get_produto_encontrado(auth_client):
    _criar_produto(auth_client, "PROD_GET")
    resp = auth_client.get("/api/produtos/PROD_GET")
    assert resp.status_code == 200
    assert resp.get_json()["id"] == "PROD_GET"


def test_get_produto_inexistente(auth_client):
    resp = auth_client.get("/api/produtos/NAO_EXISTE")
    assert resp.status_code == 404


def test_atualizar_produto(auth_client):
    _criar_produto(auth_client, "PROD_UPD")
    resp = auth_client.put(
        "/api/produtos/PROD_UPD",
        json={"nome": "Atualizado", "categoria": "Cat", "preco": 20.0,
              "quantidade": 8, "minimo": 1, "localizacao": "B2"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["produto"]["nome"] == "Atualizado"


def test_atualizar_produto_inexistente(auth_client):
    resp = auth_client.put(
        "/api/produtos/NAO",
        json={"nome": "X", "categoria": "C", "preco": 1.0, "quantidade": 1, "minimo": 0},
    )
    assert resp.status_code == 404


def test_deletar_produto(auth_client):
    _criar_produto(auth_client, "PROD_DEL")
    resp = auth_client.delete("/api/produtos/PROD_DEL")
    assert resp.status_code == 200


def test_deletar_produto_inexistente(auth_client):
    resp = auth_client.delete("/api/produtos/NAO")
    assert resp.status_code == 404


# --- Entrada / Saída --------------------------------------------------------


def test_entrada_estoque(auth_client):
    _criar_produto(auth_client, "PROD_ENT", quantidade=5)
    resp = auth_client.post("/api/entrada", json={"id": "PROD_ENT", "quantidade": 10})
    assert resp.status_code == 200
    assert auth_client.get("/api/produtos/PROD_ENT").get_json()["quantidade"] == 15


def test_saida_estoque(auth_client):
    _criar_produto(auth_client, "PROD_SAI", quantidade=10)
    resp = auth_client.post("/api/saida", json={"id": "PROD_SAI", "quantidade": 4})
    assert resp.status_code == 200
    assert auth_client.get("/api/produtos/PROD_SAI").get_json()["quantidade"] == 6


def test_saida_estoque_insuficiente(auth_client):
    _criar_produto(auth_client, "PROD_INS", quantidade=2)
    resp = auth_client.post("/api/saida", json={"id": "PROD_INS", "quantidade": 100})
    assert resp.status_code == 400


# --- Relatórios -------------------------------------------------------------


def test_relatorio_resumo(auth_client):
    resp = auth_client.get("/api/relatorios/resumo")
    assert resp.status_code == 200
    assert "estatisticas" in resp.get_json()


def test_relatorio_estoque_baixo(auth_client):
    _criar_produto(auth_client, "PROD_BAIXO", quantidade=1, minimo=10)
    resp = auth_client.get("/api/relatorios/estoque-baixo")
    assert resp.status_code == 200
    assert any(p["id"] == "PROD_BAIXO" for p in resp.get_json())


def test_relatorio_top_produtos(auth_client):
    resp = auth_client.get("/api/relatorios/top-produtos")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_relatorio_por_categoria(auth_client):
    _criar_produto(auth_client, "PROD_CAT", **{"categoria": "Especial"})
    resp = auth_client.get("/api/relatorios/por-categoria")
    assert resp.status_code == 200


# --- Histórico --------------------------------------------------------------


def test_historico_admin(auth_client):
    resp = auth_client.get("/api/historico")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_historico_negado_usuario(user_client):
    resp = user_client.get("/api/historico")
    assert resp.status_code == 403


# --- Usuários ---------------------------------------------------------------


def test_listar_usuarios_admin(auth_client):
    resp = auth_client.get("/api/users")
    assert resp.status_code == 200
    usernames = {u["username"] for u in resp.get_json()}
    assert "admin" in usernames


def test_listar_usuarios_negado(user_client):
    resp = user_client.get("/api/users")
    assert resp.status_code == 403


def test_criar_usuario_api(auth_client):
    resp = auth_client.post(
        "/api/users",
        json={"username": "novo_api", "password": "Senha123", "role": "usuario"},
    )
    assert resp.status_code == 201


def test_criar_usuario_api_duplicado(auth_client):
    auth_client.post("/api/users", json={"username": "dup_api", "password": "Senha123"})
    resp = auth_client.post("/api/users", json={"username": "dup_api", "password": "Senha123"})
    assert resp.status_code == 400


def test_criar_usuario_api_pj_incompleto(auth_client):
    resp = auth_client.post(
        "/api/users",
        json={"username": "pj_incompleto", "password": "Senha123", "tipo_contrato": "PJ"},
    )
    assert resp.status_code == 400


def test_get_usuario_detalhes(auth_client, admin_user):
    resp = auth_client.get(f"/api/users/{admin_user.id}")
    assert resp.status_code == 200
    assert resp.get_json()["username"] == "admin"


def test_atualizar_usuario_propria_conta_negado(auth_client, admin_user):
    resp = auth_client.put(f"/api/users/{admin_user.id}", json={"area": "TI"})
    assert resp.status_code == 403


def test_atualizar_usuario_outro(auth_client, criar_usuario):
    alvo = criar_usuario(username="alvo_upd")
    resp = auth_client.put(f"/api/users/{alvo.id}", json={"area": "Financeiro"})
    assert resp.status_code == 200


def test_deletar_usuario_propria_conta_negado(auth_client, admin_user):
    resp = auth_client.delete(f"/api/users/{admin_user.id}")
    assert resp.status_code == 403


def test_deletar_usuario_outro(auth_client, criar_usuario):
    alvo = criar_usuario(username="alvo_del")
    resp = auth_client.delete(f"/api/users/{alvo.id}")
    assert resp.status_code == 200


def test_resetar_senha_usuario(auth_client, criar_usuario):
    alvo = criar_usuario(username="alvo_reset")
    resp = auth_client.put(
        f"/api/users/{alvo.id}/reset-password",
        json={"nova_senha": "NovaSenha1", "confirm_nova_senha": "NovaSenha1"},
    )
    assert resp.status_code == 200


def test_atualizar_senha_propria(user_client):
    resp = user_client.put(
        "/api/users/me/password",
        json={
            "senha_atual": "Senha123",
            "senha_atual_rep": "Senha123",
            "nova_senha": "OutraSenha1",
            "confirm_nova_senha": "OutraSenha1",
        },
    )
    assert resp.status_code == 200


def test_atualizar_senha_propria_atual_incorreta(user_client):
    resp = user_client.put(
        "/api/users/me/password",
        json={
            "senha_atual": "Errada1",
            "senha_atual_rep": "Errada1",
            "nova_senha": "OutraSenha1",
            "confirm_nova_senha": "OutraSenha1",
        },
    )
    assert resp.status_code == 400


# --- Chamadas ---------------------------------------------------------------


def _criar_chamada(client, mensagem="Preciso de ajuda"):
    return client.post(
        "/api/chamadas",
        json={"tipo": "Outros", "mensagem": mensagem},
    )


def test_criar_chamada(user_client):
    resp = _criar_chamada(user_client)
    assert resp.status_code == 201
    assert "id_chamada" in resp.get_json()


def test_listar_chamadas(auth_client):
    _criar_chamada(auth_client)
    resp = auth_client.get("/api/chamadas")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_contar_nao_lidas_admin(auth_client):
    resp = auth_client.get("/api/chamadas/nao-lidas")
    assert resp.status_code == 200
    assert "nao_lidas" in resp.get_json()


def test_marcar_chamada_como_lida(auth_client):
    id_chamada = _criar_chamada(auth_client).get_json()["id_chamada"]
    resp = auth_client.put(f"/api/chamadas/{id_chamada}/ler")
    assert resp.status_code == 200


def test_atualizar_status_chamada(auth_client):
    id_chamada = _criar_chamada(auth_client).get_json()["id_chamada"]
    resp = auth_client.put(
        f"/api/chamadas/{id_chamada}/status", json={"status": "analise"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["novo_status"] == "analise"


def test_atualizar_status_chamada_invalido(auth_client):
    id_chamada = _criar_chamada(auth_client).get_json()["id_chamada"]
    resp = auth_client.put(
        f"/api/chamadas/{id_chamada}/status", json={"status": "inexistente"}
    )
    assert resp.status_code == 400


# --- Validações de erro (caminhos 400) --------------------------------------


def test_criar_usuario_api_username_invalido(auth_client):
    resp = auth_client.post("/api/users", json={"username": "ab", "password": "Senha123"})
    assert resp.status_code == 400


def test_criar_usuario_api_senha_invalida(auth_client):
    resp = auth_client.post(
        "/api/users", json={"username": "senha_fraca_user", "password": "123"}
    )
    assert resp.status_code == 400


def test_criar_usuario_api_role_invalido(auth_client):
    resp = auth_client.post(
        "/api/users",
        json={"username": "role_invalido", "password": "Senha123", "role": "superadmin"},
    )
    assert resp.status_code == 400


def test_criar_usuario_api_email_invalido(auth_client):
    resp = auth_client.post(
        "/api/users",
        json={"username": "email_invalido", "password": "Senha123", "email": "invalido"},
    )
    assert resp.status_code == 400


def test_atualizar_usuario_role_invalido(auth_client, criar_usuario):
    alvo = criar_usuario(username="upd_role_inv")
    resp = auth_client.put(f"/api/users/{alvo.id}", json={"role": "root"})
    assert resp.status_code == 400


def test_atualizar_usuario_email_invalido(auth_client, criar_usuario):
    alvo = criar_usuario(username="upd_email_inv")
    resp = auth_client.put(f"/api/users/{alvo.id}", json={"email": "sem-arroba"})
    assert resp.status_code == 400


def test_atualizar_senha_nova_diferente_confirmacao(user_client):
    resp = user_client.put(
        "/api/users/me/password",
        json={
            "senha_atual": "Senha123",
            "senha_atual_rep": "Senha123",
            "nova_senha": "OutraSenha1",
            "confirm_nova_senha": "Divergente1",
        },
    )
    assert resp.status_code == 400


def test_criar_chamada_tipo_vazio(user_client):
    resp = user_client.post("/api/chamadas", json={"tipo": "", "mensagem": ""})
    assert resp.status_code == 400


def test_resetar_senha_api_senhas_divergentes(auth_client, criar_usuario):
    alvo = criar_usuario(username="reset_div")
    resp = auth_client.put(
        f"/api/users/{alvo.id}/reset-password",
        json={"nova_senha": "NovaSenha1", "confirm_nova_senha": "Diferente1"},
    )
    assert resp.status_code == 400


def test_get_users_anonimo_401(client):
    """Requisição anônima a uma rota de API recebe 401 JSON (não redirect HTML)."""
    resp = client.get("/api/users")
    assert resp.status_code == 401
    assert resp.is_json
    assert "error" in resp.get_json()


def test_entrada_produto_inexistente(auth_client):
    resp = auth_client.post("/api/entrada", json={"id": "NAO_EXISTE", "quantidade": 5})
    assert resp.status_code in (400, 404)


def test_marcar_lida_inexistente(auth_client):
    resp = auth_client.put("/api/chamadas/999999/ler")
    assert resp.status_code == 404


def test_atualizar_status_chamada_inexistente(auth_client):
    resp = auth_client.put("/api/chamadas/999999/status", json={"status": "lida"})
    assert resp.status_code == 404


def test_produtos_acessivel_para_usuario_comum(user_client):
    # Endpoint de leitura exige apenas autenticação (não admin).
    resp = user_client.get("/api/produtos")
    assert resp.status_code == 200


def test_relatorio_resumo_usuario_comum(user_client):
    resp = user_client.get("/api/relatorios/resumo")
    assert resp.status_code == 200


def test_criar_chamada_com_subtipo(user_client):
    resp = user_client.post(
        "/api/chamadas",
        json={"tipo": "Hardware", "subtipo": "Teclado", "mensagem": "Tecla travando"},
    )
    assert resp.status_code == 201


def test_atualizar_usuario_tipo_contrato_invalido(auth_client, criar_usuario):
    alvo = criar_usuario(username="tc_invalido")
    resp = auth_client.put(f"/api/users/{alvo.id}", json={"tipo_contrato": "XYZ"})
    assert resp.status_code == 400


def test_criar_produto_duplicado(auth_client):
    _criar_produto(auth_client, "PROD_DUP")
    resp = _criar_produto(auth_client, "PROD_DUP")
    assert resp.status_code == 400


def test_atualizar_usuario_sem_corpo(auth_client, criar_usuario):
    alvo = criar_usuario(username="sem_corpo")
    resp = auth_client.put(
        f"/api/users/{alvo.id}", data="", content_type="application/json"
    )
    assert resp.status_code == 400

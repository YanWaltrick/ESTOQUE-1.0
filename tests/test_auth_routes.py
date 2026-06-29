"""Testes das rotas de autenticação e perfil (`app/routes/auth.py`).

Cobrem login (incluindo bloqueio por força bruta), logout, reautenticação de
perfil, troca de senha/foto e recuperação de senha.
"""

from io import BytesIO

from app.auth.security import PasswordValidator
from app.models import Chamada, User
from tests.conftest import SENHA_TESTE


# --- Login ------------------------------------------------------------------


def test_login_get(client):
    resp = client.get("/login")
    assert resp.status_code == 200


def test_login_usuario_comum_redireciona_index(client, usuario_comum):
    resp = client.post(
        "/login",
        data={"username": usuario_comum.username, "password": SENHA_TESTE},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/login" not in resp.headers["Location"]


def test_login_campos_vazios(client, db_session):
    resp = client.post("/login", data={"username": "", "password": ""})
    assert resp.status_code == 200


def test_login_usuario_inexistente(client, db_session):
    resp = client.post("/login", data={"username": "nao_existe", "password": "x"})
    assert resp.status_code == 200


def test_login_conta_desativada(client, db_session, criar_usuario):
    user = criar_usuario(username="desativado")
    user.ativo = False
    db_session.commit()
    resp = client.post(
        "/login", data={"username": "desativado", "password": SENHA_TESTE}
    )
    assert resp.status_code == 200


def test_login_bloqueio_forca_bruta(client, db_session, criar_usuario):
    """Após 5 senhas erradas a conta bloqueia; a 6ª tentativa NÃO deve dar 500.

    Regressão do bug de comparação naive/aware corrigido em `User`.
    """
    criar_usuario(username="alvo_bf")
    for _ in range(5):
        client.post("/login", data={"username": "alvo_bf", "password": "ERRADA"})

    # Conta agora bloqueada — tentativa seguinte é tratada graciosamente (200).
    resp = client.post("/login", data={"username": "alvo_bf", "password": SENHA_TESTE})
    assert resp.status_code == 200

    user = User.query.filter_by(username="alvo_bf").first()
    assert user.bloqueado_ate is not None
    assert user.pode_tentar_login() is False  # não levanta TypeError


def test_logout(auth_client):
    resp = auth_client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# --- Perfil / reautenticação ------------------------------------------------


def test_perfil_get_sem_verificacao(user_client):
    # Sem perfil_verified, exibe o formulário de reautenticação (200).
    resp = user_client.get("/perfil")
    assert resp.status_code == 200


def test_perfil_reautenticacao_correta(user_client, usuario_comum):
    resp = user_client.post(
        "/perfil",
        data={"username": usuario_comum.username, "password": SENHA_TESTE},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    # A reautenticação bem-sucedida marca a sessão como verificada (o caminho de
    # falha também devolve 302, então o status sozinho não distinguiria os dois).
    with user_client.session_transaction() as sess:
        assert sess.get("perfil_verified") is True


def test_perfil_senha_sem_verificacao_redireciona(user_client):
    resp = user_client.get("/perfil/senha", follow_redirects=False)
    assert resp.status_code == 302


def test_trocar_senha_fluxo_completo(perfil_verificado_client, usuario_comum):
    resp = perfil_verificado_client.post(
        "/perfil/password",
        data={
            "login_name": usuario_comum.username,
            "senha_atual": SENHA_TESTE,
            "nova_senha": "NovaSenha1",
            "confirm_nova_senha": "NovaSenha1",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    # A senha deve ter sido efetivamente alterada no banco (o caminho de erro
    # redireciona com o mesmo 302, então é preciso verificar o efeito).
    user = User.query.filter_by(username=usuario_comum.username).first()
    assert PasswordValidator.verify_password("NovaSenha1", user.password)
    assert not PasswordValidator.verify_password(SENHA_TESTE, user.password)


def test_trocar_senha_atual_incorreta(perfil_verificado_client, usuario_comum):
    resp = perfil_verificado_client.post(
        "/perfil/password",
        data={
            "login_name": usuario_comum.username,
            "senha_atual": "Errada1",
            "nova_senha": "NovaSenha1",
            "confirm_nova_senha": "NovaSenha1",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302  # redireciona com flash de erro
    # Senha atual incorreta: a senha NÃO deve mudar.
    user = User.query.filter_by(username=usuario_comum.username).first()
    assert PasswordValidator.verify_password(SENHA_TESTE, user.password)


def test_perfil_foto_get(perfil_verificado_client):
    resp = perfil_verificado_client.get("/perfil/foto")
    assert resp.status_code == 200


def test_perfil_foto_upload_valido(perfil_verificado_client, usuario_comum):
    data = {"foto_perfil": (BytesIO(b"\x89PNG\r\n\x1a\nconteudo"), "foto.png")}
    resp = perfil_verificado_client.post(
        "/perfil/foto", data=data, content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    # A referência da nova foto deve ter sido gravada no usuário (o caminho de
    # erro também redireciona com 302, então é preciso verificar o efeito).
    user = User.query.filter_by(username=usuario_comum.username).first()
    assert user.foto_perfil
    assert user.foto_perfil.lower().endswith(".png")


def test_perfil_foto_extensao_invalida(perfil_verificado_client, usuario_comum):
    data = {"foto_perfil": (BytesIO(b"conteudo"), "arquivo.exe")}
    resp = perfil_verificado_client.post(
        "/perfil/foto", data=data, content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code == 302  # redireciona com flash de erro
    # Extensão não permitida: nada deve ser gravado no usuário.
    user = User.query.filter_by(username=usuario_comum.username).first()
    assert not user.foto_perfil


def test_perfil_foto_sem_arquivo(perfil_verificado_client, usuario_comum):
    resp = perfil_verificado_client.post(
        "/perfil/foto", data={}, content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    user = User.query.filter_by(username=usuario_comum.username).first()
    assert not user.foto_perfil


# --- Recuperação de senha ---------------------------------------------------


def test_forgot_password_get(client):
    resp = client.get("/forgot-password")
    assert resp.status_code == 200


def test_forgot_password_username_vazio(client, db_session):
    resp = client.post("/forgot-password", data={"username": ""}, follow_redirects=False)
    assert resp.status_code == 302


def test_forgot_password_cria_chamado(client, db_session, criar_usuario):
    user = criar_usuario(username="esqueci")
    resp = client.post(
        "/forgot-password",
        data={"username": "esqueci", "mensagem": "Esqueci minha senha"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    # Deve ter sido aberto um chamado de redefinição para o usuário (o caminho de
    # username vazio/inexistente também devolve 302 com a mesma mensagem genérica).
    chamada = Chamada.query.filter_by(id_usuario=user.id).first()
    assert chamada is not None
    assert "Esqueci minha senha" in chamada.mensagem


# --- Arquivos do usuário ----------------------------------------------------


def test_user_files(user_client):
    resp = user_client.get("/user-files")
    assert resp.status_code == 200


def test_download_arquivo_inexistente(user_client):
    resp = user_client.get("/download/arquivo_que_nao_existe.pdf", follow_redirects=False)
    assert resp.status_code == 302


# --- Perfil já verificado ---------------------------------------------------


def test_perfil_get_verificado(perfil_verificado_client):
    resp = perfil_verificado_client.get("/perfil")
    assert resp.status_code == 200


def test_perfil_senha_get_verificado(perfil_verificado_client):
    resp = perfil_verificado_client.get("/perfil/senha")
    assert resp.status_code == 200

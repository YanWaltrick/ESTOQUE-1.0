"""Testes unitários dos modelos (`app/models/__init__.py`).

Cobrem métodos de instância e `to_dict`. Os métodos que persistem
(`registrar_login_*`, `pode_tentar_login`, `is_active`) usam `db_session`.
"""

from datetime import timedelta

from app.models import (
    Chamada,
    Historico,
    ItemRecebido,
    Movimentacao,
    Produto,
    TermoEntrega,
    User,
    now_gmt3,
)

# --- Produto ----------------------------------------------------------------


def test_produto_valor_total():
    p = Produto("P1", "Mouse", "Periféricos", preco=50.0, quantidade=4, minimo=2)
    assert p.valor_total() == 200.0


def test_produto_abaixo_minimo_true():
    p = Produto("P1", "Mouse", "Periféricos", preco=50.0, quantidade=1, minimo=5)
    assert p.abaixo_minimo() is True


def test_produto_abaixo_minimo_false():
    p = Produto("P1", "Mouse", "Periféricos", preco=50.0, quantidade=10, minimo=5)
    assert p.abaixo_minimo() is False


def test_produto_to_dict():
    p = Produto("P9", "Teclado", "Periféricos", preco=100.0, quantidade=3, minimo=1)
    d = p.to_dict()
    assert d["id"] == "P9"
    assert d["nome"] == "Teclado"
    assert d["valor_total"] == 300.0
    assert d["abaixo_minimo"] is False
    # Sem persistir, data_criacao é None -> formatação trata como None.
    assert d["data_criacao"] is None


# --- User: propriedades e construtor ----------------------------------------


def test_user_is_admin_true():
    u = User(username="x", password="h", role="admin")
    assert u.is_admin is True


def test_user_is_admin_false():
    u = User(username="x", password="h", role="usuario")
    assert u.is_admin is False


def test_user_construtor_normaliza_tipo_contrato():
    u = User(username="x", password="h", tipo_contrato="pj")
    assert u.tipo_contrato == "PJ"


def test_user_construtor_faz_strip_dos_campos():
    u = User(username="x", password="h", area="  TI  ", empresa=" ACME ")
    assert u.area == "TI"
    assert u.empresa == "ACME"


def test_user_to_dict_nao_expoe_password():
    u = User(username="joao", password="hash-secreto", role="usuario")
    d = u.to_dict()
    assert "password" not in d
    assert d["username"] == "joao"
    assert d["is_admin"] is False
    assert d["ultimo_login"] == "Nunca"


# --- User: segurança / força bruta (precisam de db_session) ------------------


def test_registrar_login_falho_incrementa(db_session, criar_usuario):
    u = criar_usuario(username="bf_user")
    u.registrar_login_falho()
    assert u.tentativas_login_falhas == 1
    assert u.bloqueado_ate is None


def test_bloqueio_apos_5_tentativas(db_session, criar_usuario):
    u = criar_usuario(username="bf_user2")
    for _ in range(5):
        u.registrar_login_falho()
    assert u.tentativas_login_falhas == 5
    assert u.bloqueado_ate is not None
    assert u.pode_tentar_login() is False
    assert u.minutos_ate_desbloqueio() > 0


def test_pode_tentar_login_quando_nao_bloqueado(db_session, criar_usuario):
    u = criar_usuario(username="ok_user")
    assert u.pode_tentar_login() is True
    assert u.minutos_ate_desbloqueio() == 0


def test_bloqueio_expirado_libera(db_session, criar_usuario):
    u = criar_usuario(username="exp_user")
    # Bloqueio no passado -> deve liberar e zerar tentativas.
    u.tentativas_login_falhas = 5
    u.bloqueado_ate = now_gmt3() - timedelta(minutes=1)
    db_session.commit()
    assert u.pode_tentar_login() is True
    assert u.bloqueado_ate is None
    assert u.tentativas_login_falhas == 0


def test_registrar_login_sucesso_reseta(db_session, criar_usuario):
    u = criar_usuario(username="suc_user")
    u.tentativas_login_falhas = 3
    db_session.commit()
    u.registrar_login_sucesso()
    assert u.tentativas_login_falhas == 0
    assert u.bloqueado_ate is None
    assert u.ultimo_login is not None


def test_is_active_inativo(db_session, criar_usuario):
    u = criar_usuario(username="inativo_user")
    u.ativo = False
    db_session.commit()
    assert u.is_active is False


def test_is_active_ativo(db_session, criar_usuario):
    u = criar_usuario(username="ativo_user")
    assert u.is_active is True


# --- Movimentacao / Chamada / Historico / ItemRecebido / TermoEntrega -------


def test_movimentacao_construtor():
    m = Movimentacao("P1", "ENTRADA", 5, motivo="compra", usuario="admin")
    assert m.id_produto == "P1"
    assert m.tipo == "ENTRADA"
    assert m.quantidade == 5
    assert m.motivo == "compra"


def test_chamada_to_dict_sem_usuario():
    c = Chamada(id_usuario=1, mensagem="Preciso de ajuda")
    d = c.to_dict()
    assert d["mensagem"] == "Preciso de ajuda"
    assert d["status"] == "nova"
    assert d["lida"] is False
    assert d["usuario"] == "Desconhecido"


def test_historico_to_dict():
    h = Historico("login", "Usuário logou", usuario_responsavel="admin")
    d = h.to_dict()
    assert d["tipo_evento"] == "login"
    assert d["descricao"] == "Usuário logou"
    assert d["usuario_responsavel"] == "admin"


def test_item_recebido_to_dict():
    item = ItemRecebido(
        id_usuario=1,
        descricao_item="Notebook Dell",
        tipo_recebimento="entrada",
        usuario_responsavel="admin",
    )
    d = item.to_dict()
    assert d["descricao_item"] == "Notebook Dell"
    assert d["tipo_recebimento"] == "entrada"


def test_termo_entrega_construtor_inicializa_equipamentos_vazios():
    t = TermoEntrega(id_usuario=1, empresa="ACME")
    assert t.equipamentos == "[]"
    assert t.assinado is False
    assert t.empresa == "ACME"


def test_termo_entrega_to_dict(db_session, criar_usuario):
    u = criar_usuario(username="termo_user")
    t = TermoEntrega(id_usuario=u.id, empresa="ACME", cnpj="12.345.678/0001-90")
    db_session.add(t)
    db_session.commit()
    d = t.to_dict()
    assert d["empresa"] == "ACME"
    assert d["equipamentos"] == []  # JSON "[]" -> lista vazia
    assert d["usuario"] == "termo_user"

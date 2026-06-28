"""Testes de `app/services/estoque_service.py`.

Exercitam o CRUD de produtos, entrada/saída de estoque e relatórios contra o
banco de teste (via `db_session`).
"""

import pytest

from app.models import Produto
from app.services.estoque_service import EstoqueService


@pytest.fixture()
def servico(db_session):
    """Instância do serviço de estoque ligada à transação de teste."""
    return EstoqueService()


def _add(servico, id_produto="E1", nome="Mouse", categoria="Periféricos",
         preco=50.0, quantidade=10, minimo=2, localizacao="A1"):
    assert servico.adicionar_produto(
        id_produto, nome, categoria, preco, quantidade, minimo, localizacao
    ) is True


# --- adicionar_produto ------------------------------------------------------


def test_adicionar_produto_sucesso(servico):
    _add(servico)
    p = servico.buscar_produto("E1")
    assert p is not None
    assert p.nome == "Mouse"


def test_adicionar_produto_id_duplicado(servico):
    _add(servico, id_produto="E2")
    assert servico.adicionar_produto("E2", "Outro", "Cat", 10.0, 1, 1) is False


def test_adicionar_produto_preco_invalido(servico):
    assert servico.adicionar_produto("E3", "X", "Cat", 0, 5, 1) is False


def test_adicionar_produto_quantidade_negativa(servico):
    assert servico.adicionar_produto("E4", "X", "Cat", 10.0, -1, 1) is False


# --- buscar / listar --------------------------------------------------------


def test_buscar_produto_inexistente(servico):
    assert servico.buscar_produto("NAO_EXISTE") is None


def test_listar_produtos(servico):
    _add(servico, id_produto="L1")
    _add(servico, id_produto="L2")
    ids = {p.id_produto for p in servico.listar_produtos()}
    assert {"L1", "L2"}.issubset(ids)


# --- atualizar_quantidade ---------------------------------------------------


def test_atualizar_quantidade_sucesso(servico):
    _add(servico, id_produto="Q1", quantidade=5)
    assert servico.atualizar_quantidade("Q1", 20) is True
    assert servico.buscar_produto("Q1").quantidade == 20


def test_atualizar_quantidade_negativa(servico):
    _add(servico, id_produto="Q2")
    assert servico.atualizar_quantidade("Q2", -5) is False


def test_atualizar_quantidade_inexistente(servico):
    assert servico.atualizar_quantidade("NAO", 5) is False


# --- entrada_estoque --------------------------------------------------------


def test_entrada_estoque_incrementa(servico):
    _add(servico, id_produto="EN1", quantidade=10)
    assert servico.entrada_estoque("EN1", 5, motivo="compra") is True
    assert servico.buscar_produto("EN1").quantidade == 15
    movs = servico.get_movimentacoes("EN1")
    assert any(m.tipo == "ENTRADA" for m in movs)


def test_entrada_estoque_quantidade_invalida(servico):
    _add(servico, id_produto="EN2")
    assert servico.entrada_estoque("EN2", 0) is False


def test_entrada_estoque_inexistente(servico):
    assert servico.entrada_estoque("NAO", 5) is False


# --- saida_estoque ----------------------------------------------------------


def test_saida_estoque_decrementa(servico):
    _add(servico, id_produto="SA1", quantidade=10)
    assert servico.saida_estoque("SA1", 4, motivo="uso") is True
    assert servico.buscar_produto("SA1").quantidade == 6


def test_saida_estoque_insuficiente(servico):
    _add(servico, id_produto="SA2", quantidade=3)
    assert servico.saida_estoque("SA2", 10) is False
    assert servico.buscar_produto("SA2").quantidade == 3


def test_saida_estoque_quantidade_invalida(servico):
    _add(servico, id_produto="SA3", quantidade=5)
    assert servico.saida_estoque("SA3", -1) is False


def test_saida_estoque_inexistente(servico):
    assert servico.saida_estoque("NAO", 1) is False


# --- atualizar_produto ------------------------------------------------------


def test_atualizar_produto_sucesso(servico):
    _add(servico, id_produto="AT1")
    assert servico.atualizar_produto(
        "AT1", nome="Novo Nome", preco="99.9", quantidade="7", minimo="3"
    ) is True
    p = servico.buscar_produto("AT1")
    assert p.nome == "Novo Nome"
    assert p.preco == 99.9
    assert p.quantidade == 7


def test_atualizar_produto_inexistente(servico):
    assert servico.atualizar_produto("NAO", nome="X") is False


# --- remover_produto --------------------------------------------------------


def test_remover_produto_sucesso(servico):
    _add(servico, id_produto="RM1")
    assert servico.remover_produto("RM1") is True
    assert servico.buscar_produto("RM1") is None


def test_remover_produto_inexistente(servico):
    assert servico.remover_produto("NAO") is False


# --- relatórios -------------------------------------------------------------


def test_relatorio_estoque_baixo(servico):
    _add(servico, id_produto="RB1", quantidade=1, minimo=5)  # abaixo
    _add(servico, id_produto="RB2", quantidade=10, minimo=5)  # ok
    baixos = {p.id_produto for p in servico.relatorio_estoque_baixo()}
    assert "RB1" in baixos
    assert "RB2" not in baixos


def test_relatorio_valor_total(servico):
    _add(servico, id_produto="VT1", preco=10.0, quantidade=3)
    rel = servico.relatorio_valor_total()
    assert rel["total_produtos"] >= 1
    assert rel["valor_total"] >= 30.0


def test_relatorio_por_categoria(servico):
    _add(servico, id_produto="PC1", categoria="CatX", preco=10.0, quantidade=2)
    rel = servico.relatorio_por_categoria()
    assert "CatX" in rel
    assert rel["CatX"]["total_produtos"] >= 1


def test_get_movimentacoes_vazio(servico):
    _add(servico, id_produto="MV1")
    assert servico.get_movimentacoes("MV1") == []


# --- Migração de JSON legado ------------------------------------------------


def test_migracao_json_para_banco(db_session, monkeypatch, tmp_path):
    """Com `dados_estoque.json` no cwd e banco vazio, o serviço migra e faz backup."""
    import json

    dados = {
        "JSON1": {
            "nome": "Item JSON",
            "categoria": "Migrados",
            "preco": 15.0,
            "quantidade": 4,
            "minimo": 1,
            "localizacao": "Z9",
        }
    }
    (tmp_path / "dados_estoque.json").write_text(json.dumps(dados), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    servico = EstoqueService()  # __init__ dispara a migração

    assert servico.buscar_produto("JSON1") is not None
    assert (tmp_path / "dados_estoque.json.backup").exists()
    assert not (tmp_path / "dados_estoque.json").exists()

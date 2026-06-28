"""Testes de `app/services/termo_service.py`.

Exercitam a geração do PDF do Termo de Entrega (CLT e PJ, termo e aditivo, com
e sem equipamentos) via ReportLab — sem mock, validando que o resultado é um
PDF bem-formado. Usam `db_session` (app context + banco de teste).
"""

import json
from datetime import date
from io import BytesIO

import pytest

from app.models import TermoEntrega
from app.services.termo_service import TermoService

EQUIPAMENTOS = json.dumps(
    [
        {
            "descricao": "Notebook Dell Latitude",
            "marca": "Dell",
            "modelo": "5440",
            "estado": "Novo",
            "data_entrega": "15/01/2024",
            "valor": "5000",
            "fotos": [],
        },
        {
            "descricao": "Mouse sem fio",
            "marca": "Logitech",
            "modelo": "M170",
            "estado": "Novo",
            "data_entrega": "15/01/2024",
            "valor": "80",
            "fotos": [],
        },
    ]
)


def _criar_termo(db_session, user, **kwargs):
    termo = TermoEntrega(id_usuario=user.id, **kwargs)
    db_session.add(termo)
    db_session.commit()
    return termo


def _eh_pdf(resultado):
    if isinstance(resultado, BytesIO):
        dados = resultado.getvalue()
    else:
        with open(resultado, "rb") as f:
            dados = f.read()
    return dados[:4] == b"%PDF" and len(dados) > 1000


# --- CLT --------------------------------------------------------------------


def test_gerar_pdf_clt_com_equipamentos(db_session, criar_usuario):
    user = criar_usuario(
        username="clt_user",
        tipo_contrato="CLT",
        empresa="ACME LTDA",
        cnpj="12.345.678/0001-90",
        cargo="Analista",
        cpf="123.456.789-00",
        data_admissao=date(2024, 1, 15),
    )
    _criar_termo(
        db_session,
        user,
        empresa="ACME LTDA",
        cnpj="12.345.678/0001-90",
        nome_colaborador="CLT User",
        cargo_funcao="Analista",
        cpf_cnpj="123.456.789-00",
    )
    db_session.query(TermoEntrega).filter_by(id_usuario=user.id).update(
        {"equipamentos": EQUIPAMENTOS}
    )
    db_session.commit()

    resultado = TermoService.gerar_pdf(user.id)
    assert _eh_pdf(resultado)


def test_gerar_pdf_clt_sem_equipamentos(db_session, criar_usuario):
    user = criar_usuario(username="clt_vazio", tipo_contrato="CLT")
    _criar_termo(db_session, user, nome_colaborador="CLT Vazio")
    resultado = TermoService.gerar_pdf(user.id)
    assert _eh_pdf(resultado)


def test_gerar_pdf_clt_aditivo(db_session, criar_usuario):
    user = criar_usuario(username="clt_aditivo", tipo_contrato="CLT")
    termo = _criar_termo(db_session, user, nome_colaborador="CLT Aditivo")
    termo.equipamentos = EQUIPAMENTOS
    db_session.commit()
    resultado = TermoService.gerar_pdf(user.id, aditivo=True)
    assert _eh_pdf(resultado)


# --- PJ ---------------------------------------------------------------------


def test_gerar_pdf_pj_com_equipamentos(db_session, criar_usuario):
    user = criar_usuario(
        username="pj_user",
        tipo_contrato="PJ",
        pj_contratante="Contratante SA",
        pj_contratante_cnpj="98.765.432/0001-10",
        pj_contratada="Contratada ME",
        pj_contratada_cnpj="11.222.333/0001-44",
        pj_data_contrato=date(2024, 2, 1),
    )
    termo = _criar_termo(
        db_session,
        user,
        pj_contratante="Contratante SA",
        pj_contratante_cnpj="98.765.432/0001-10",
        pj_contratada="Contratada ME",
        pj_contratada_cnpj="11.222.333/0001-44",
    )
    termo.equipamentos = EQUIPAMENTOS
    db_session.commit()
    resultado = TermoService.gerar_pdf(user.id)
    assert _eh_pdf(resultado)


def test_gerar_pdf_pj_aditivo(db_session, criar_usuario):
    user = criar_usuario(username="pj_aditivo", tipo_contrato="PJ", pj_contratada="Contratada ME")
    termo = _criar_termo(db_session, user, pj_contratada="Contratada ME")
    termo.equipamentos = EQUIPAMENTOS
    db_session.commit()
    resultado = TermoService.gerar_pdf(user.id, aditivo=True)
    assert _eh_pdf(resultado)


# --- Saída em arquivo -------------------------------------------------------


def test_gerar_pdf_escreve_arquivo(db_session, criar_usuario, tmp_path):
    user = criar_usuario(username="clt_arquivo", tipo_contrato="CLT")
    _criar_termo(db_session, user, nome_colaborador="Arquivo")
    destino = str(tmp_path / "termo.pdf")
    resultado = TermoService.gerar_pdf(user.id, nome_arquivo=destino)
    assert resultado == destino
    assert _eh_pdf(destino)


# --- Erros ------------------------------------------------------------------


def test_gerar_pdf_usuario_inexistente(db_session):
    with pytest.raises(ValueError, match="nao encontrado"):
        TermoService.gerar_pdf(999999)


def test_gerar_pdf_termo_inexistente(db_session, criar_usuario):
    user = criar_usuario(username="sem_termo")
    with pytest.raises(ValueError, match="Termo"):
        TermoService.gerar_pdf(user.id)


# --- Laudo fotográfico ------------------------------------------------------


def test_gerar_pdf_com_fotos(db_session, criar_usuario, app):
    """Equipamento com foto real exercita o laudo fotográfico do PDF."""
    import os

    from PIL import Image

    termos_dir = os.path.join(app.static_folder, "uploads", "termos")
    os.makedirs(termos_dir, exist_ok=True)
    foto_path = os.path.join(termos_dir, "teste_foto_termo.png")
    Image.new("RGB", (120, 90), color="blue").save(foto_path)

    try:
        user = criar_usuario(username="foto_termo", tipo_contrato="CLT")
        termo = TermoEntrega(id_usuario=user.id, nome_colaborador="Foto")
        termo.equipamentos = json.dumps(
            [
                {
                    "descricao": "Notebook",
                    "marca": "Dell",
                    "modelo": "5440",
                    "estado": "Novo",
                    "service_tag": "ABC123",
                    "fotos": [{"arquivo": "teste_foto_termo.png", "titulo": "Frente"}],
                }
            ]
        )
        db_session.add(termo)
        db_session.commit()

        resultado = TermoService.gerar_pdf(user.id)
        assert _eh_pdf(resultado)
    finally:
        if os.path.exists(foto_path):
            os.remove(foto_path)

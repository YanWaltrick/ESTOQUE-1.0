"""Testes unitários de `app/auth/security.py`.

Cobrem o `PasswordValidator` (validação, score, hash/verify) e as funções
`validate_username` / `validate_email`. São funções puras: não precisam de app
context nem banco.
"""

import pytest

from app.auth.security import PasswordValidator, validate_email, validate_username


# --- PasswordValidator.validate ---------------------------------------------


def test_senha_valida_passa():
    valido, erros = PasswordValidator.validate("Abc123")
    assert valido is True
    assert erros == []


def test_senha_vazia_reprovada():
    valido, erros = PasswordValidator.validate("")
    assert valido is False
    assert "Senha não pode estar vazia" in erros


def test_senha_curta_reprovada():
    valido, erros = PasswordValidator.validate("Ab1")
    assert valido is False
    assert any("mínimo" in e for e in erros)


def test_senha_sem_maiuscula_reprovada():
    valido, erros = PasswordValidator.validate("abc123def")
    assert valido is False
    assert any("maiúscula" in e for e in erros)


def test_senha_sem_minuscula_reprovada():
    valido, erros = PasswordValidator.validate("ABC123DEF")
    assert valido is False
    assert any("minúscula" in e for e in erros)


def test_senha_sem_digito_reprovada():
    valido, erros = PasswordValidator.validate("AbcDefGhi")
    assert valido is False
    assert any("número" in e for e in erros)


def test_senha_apenas_minusculas_e_fraca():
    valido, erros = PasswordValidator.validate("abcdef")
    assert valido is False
    assert any("fraca" in e for e in erros)


def test_senha_com_sequencia_comum_fraca():
    # "123abc" começa com sequência comum -> _is_weak_password True
    valido, erros = PasswordValidator.validate("123abc")
    assert valido is False
    assert any("fraca" in e for e in erros)


def test_senha_caracteres_repetidos_reprovada():
    valido, _ = PasswordValidator.validate("aaaaaa")
    assert valido is False


# --- _is_weak_password ------------------------------------------------------


@pytest.mark.parametrize(
    "senha",
    ["abcdef", "ABCDEF", "123456", "aaaa", "234567"],
)
def test_is_weak_password_detecta_padroes(senha):
    assert PasswordValidator._is_weak_password(senha) is True


def test_is_weak_password_aceita_forte():
    assert PasswordValidator._is_weak_password("Abc123") is False


# --- strength_score ---------------------------------------------------------


def test_strength_score_entre_0_e_100():
    score = PasswordValidator.strength_score("Abc123")
    assert 0 <= score <= 100


def test_strength_score_senha_forte_maior_que_fraca():
    forte = PasswordValidator.strength_score("MyLongPassword123!@#")
    fraca = PasswordValidator.strength_score("abcdef")
    assert forte > fraca


def test_strength_score_invalida_penalizada():
    # Senha que falha validate() recebe penalidade.
    assert PasswordValidator.strength_score("a") < 50


def test_strength_score_senha_vazia():
    assert PasswordValidator.strength_score("") == 0


# --- hash_password / verify_password ----------------------------------------


def test_hash_password_gera_hash_diferente_da_senha():
    h = PasswordValidator.hash_password("Abc123")
    assert h
    assert h != "Abc123"


def test_hash_password_usa_salt_aleatorio():
    h1 = PasswordValidator.hash_password("Abc123")
    h2 = PasswordValidator.hash_password("Abc123")
    assert h1 != h2  # salt aleatório por hash


def test_verify_password_correta():
    h = PasswordValidator.hash_password("Abc123")
    assert PasswordValidator.verify_password("Abc123", h) is True


def test_verify_password_incorreta():
    h = PasswordValidator.hash_password("Abc123")
    assert PasswordValidator.verify_password("Errada1", h) is False


# --- validate_username ------------------------------------------------------


@pytest.mark.parametrize(
    "username",
    ["usuario", "user_name", "user-name", "user.name", "user 123", "user123"],
)
def test_validate_username_validos(username):
    valido, erro = validate_username(username)
    assert valido is True
    assert erro == ""


def test_validate_username_email_valido_aceito():
    valido, erro = validate_username("user@example.com")
    assert valido is True
    assert erro == ""


def test_validate_username_vazio():
    valido, erro = validate_username("")
    assert valido is False
    assert "vazio" in erro


def test_validate_username_curto():
    valido, erro = validate_username("ab")
    assert valido is False
    assert "mínimo" in erro


def test_validate_username_longo():
    valido, erro = validate_username("x" * 151)
    assert valido is False
    assert "150" in erro


def test_validate_username_caractere_invalido():
    valido, erro = validate_username("user!name")
    assert valido is False
    assert "letras" in erro


def test_validate_username_email_invalido():
    valido, erro = validate_username("user@invalido")
    assert valido is False
    assert "Email inválido" in erro


# --- validate_email ---------------------------------------------------------


@pytest.mark.parametrize(
    "email",
    [
        "user@example.com",
        "user.name@example.com",
        "user+tag@example.com",
        "user_name@sub.example.co.uk",
    ],
)
def test_validate_email_validos(email):
    valido, erro = validate_email(email)
    assert valido is True
    assert erro == ""


@pytest.mark.parametrize(
    "email",
    ["", "user", "user@", "user@.com", "user@example", "user @example.com"],
)
def test_validate_email_invalidos(email):
    valido, erro = validate_email(email)
    assert valido is False
    assert erro

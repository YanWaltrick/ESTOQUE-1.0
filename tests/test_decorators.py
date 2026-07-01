"""Testes de `app/auth/decorators.py`.

Cobrem as funções auxiliares de permissão (puras e dependentes de
`current_user`). Os decoradores `require_role`/`require_permission` são
exercitados de ponta a ponta nos testes de rota (`test_api.py`,
`test_admin.py`).
"""

from flask_login import login_user

from app.auth.decorators import (
    ROLES_PERMISSIONS,
    can_perform,
    get_available_roles,
    get_role_permissions,
    get_user_permissions,
)

# --- Funções puras ----------------------------------------------------------


def test_get_available_roles():
    roles = get_available_roles()
    assert "admin" in roles
    assert "usuario" in roles


def test_get_role_permissions_admin():
    perms = get_role_permissions("admin")
    assert "delete_user" in perms
    assert "manage_users" in perms


def test_get_role_permissions_usuario():
    assert get_role_permissions("usuario") == ["criar_chamado"]


def test_get_role_permissions_inexistente():
    assert get_role_permissions("inexistente") == []


# --- can_perform / get_user_permissions (dependem de current_user) ----------


def test_can_perform_nao_autenticado(app):
    with app.test_request_context():
        assert can_perform("criar_chamado") is False


def test_get_user_permissions_nao_autenticado(app):
    with app.test_request_context():
        assert get_user_permissions() == []


def test_can_perform_admin(app, db_session, criar_usuario):
    admin = criar_usuario(username="dec_admin", role="admin")
    with app.test_request_context():
        login_user(admin)
        assert can_perform("delete_user") is True
        assert can_perform("manage_users") is True
        assert get_user_permissions() == ROLES_PERMISSIONS["admin"]


def test_can_perform_usuario_comum(app, db_session, criar_usuario):
    user = criar_usuario(username="dec_user", role="usuario")
    with app.test_request_context():
        login_user(user)
        assert can_perform("criar_chamado") is True
        assert can_perform("delete_user") is False
        assert get_user_permissions() == ["criar_chamado"]

"""
Decoradores RBAC (Role-Based Access Control) para controlar acesso baseado em roles.

Uso:
    @require_role('admin')              # Apenas admin
    @require_role(['admin', 'usuario']) # Admin ou usuário
    @require_permission('delete_user')  # Requer permissão específica
"""

from functools import wraps
from flask import redirect, url_for, flash, abort, jsonify
from flask_login import current_user


# Definição de roles e suas permissões
ROLES_PERMISSIONS = {
    'admin': [
        'view_dashboard',
        'manage_users',
        'delete_user',
        'create_user',
        'edit_product',
        'delete_product',
        'view_reports',
        'view_audit_log',
        'manage_chamadas',
        'create_produto',
        'edit_user',
        'registrar_entrada',
        'registrar_saida',
        'view_estoque',
        'criar_chamado'
    ],
    'usuario': [
        'criar_chamado'
    ]
}


def require_role(*allowed_roles):
    """
    Decorador para exigir um ou mais roles específicos.
    
    Args:
        *allowed_roles: String ou lista de strings com roles permitidos
        
    Exemplo:
        @require_role('admin')
        @require_role('admin', 'usuario')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Se não está autenticado
            if not current_user.is_authenticated:
                flash('Por favor, faça login para acessar questa página.', 'error')
                return redirect(url_for('auth.login'))
            
            # Normalizar allowed_roles em lista
            roles = allowed_roles[0] if isinstance(allowed_roles[0], (list, tuple)) else allowed_roles
            
            # Verificar se o role do usuário está na lista de permitidos
            if current_user.role not in roles:
                flash(f'Acesso negado. Você precisa ser {" ou ".join(roles)}.', 'error')
                # Se é uma requisição AJAX, retornar JSON
                from flask import request
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Acesso negado'}), 403
                abort(403)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_permission(permission):
    """
    Decorador para exigir uma permissão específica.
    
    Args:
        permission: String com o nome da permissão
        
    Exemplo:
        @require_permission('delete_user')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Se não está autenticado
            if not current_user.is_authenticated:
                flash('Por favor, faça login para acessar esta página.', 'error')
                return redirect(url_for('auth.login'))
            
            # Obter permissões do role
            permissions = ROLES_PERMISSIONS.get(current_user.role, [])
            
            # Verificar se tem a permissão
            if permission not in permissions:
                flash(f'Acesso negado. Você não tem permissão para: {permission}', 'error')
                from flask import request
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Acesso negado'}), 403
                abort(403)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_authenticated():
    """
    Decorador para exigir que o usuário esteja autenticado.
    Similar ao login_required, mas com melhor tratamento de erros.
    
    Exemplo:
        @require_authenticated()
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Por favor, faça login para acessar esta página.', 'error')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def can_perform(permission):
    """
    Função auxiliar para verificar se o usuário pode realizar uma ação.
    Usar em templates/views para controle condicional.
    
    Args:
        permission: String com o nome da permissão
        
    Retorna:
        Boolean - True se tem permissão, False caso contrário
        
    Exemplo em template:
        {% if can_perform('delete_user') %}
            <button>Deletar Usuário</button>
        {% endif %}
        
    Exemplo em view:
        if can_perform('edit_product'):
            # fazer algo
    """
    if not current_user.is_authenticated:
        return False
    
    permissions = ROLES_PERMISSIONS.get(current_user.role, [])
    return permission in permissions


def get_user_permissions():
    """
    Retorna lista de permissões do usuário atual.
    
    Retorna:
        Lista vazia se não autenticado, lista de permissões se autenticado
    """
    if not current_user.is_authenticated:
        return []
    
    return ROLES_PERMISSIONS.get(current_user.role, [])


def get_available_roles():
    """
    Retorna lista de todos os roles disponíveis.
    """
    return list(ROLES_PERMISSIONS.keys())


def get_role_permissions(role):
    """
    Retorna lista de permissões de um role específico.
    
    Args:
        role: String com o nome do role
        
    Retorna:
        Lista de permissões ou lista vazia se role não existe
    """
    return ROLES_PERMISSIONS.get(role, [])

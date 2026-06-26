"""
Módulo de integração com Microsoft Entra ID (Azure AD) usando MSAL.

Este módulo fornece funções auxiliares para:
- Construir a URL de autenticação da Microsoft
- Processar o código de autorização
- Validar e decodificar tokens JWT
- Limpar sessões ao fazer logout
"""

import os
import json
import secrets
import msal
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from werkzeug.security import generate_password_hash
from app.database import db
from app.models import User


class EntraIDConfig:
    """Configuração centralizada para Microsoft Entra ID."""
    
    def __init__(self):
        """Inicializa a configuração a partir de variáveis de ambiente."""
        self.client_id = os.getenv('ENTRA_CLIENT_ID')
        self.client_secret = os.getenv('ENTRA_CLIENT_SECRET')
        self.tenant_id = os.getenv('ENTRA_TENANT_ID')
        self.authority = os.getenv(
            'ENTRA_AUTHORITY',
            f'https://login.microsoftonline.com/{self.tenant_id}'
        )
        self.redirect_path = os.getenv('ENTRA_REDIRECT_PATH', '/entra-callback')
        # MSAL Python adiciona automaticamente os escopos reservados openid/profile
        self.scopes = ['User.Read']  # Escopo Graph para ler perfil do usuário
        
        # Validação básica
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            raise ValueError(
                'Variáveis de ambiente ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET '
                'e ENTRA_TENANT_ID são obrigatórias'
            )
    
    def get_redirect_uri(self, base_url: str) -> str:
        """
        Constrói a URI completa de redirecionamento.
        
        Args:
            base_url: URL base da aplicação (ex: http://localhost:5000)
            
        Returns:
            URI completa de callback (ex: http://localhost:5000/entra-callback)
        """
        return f"{base_url}{self.redirect_path}"


class EntraIDClient:
    """Cliente para gerenciar fluxo de autenticação com Entra ID."""
    
    def __init__(self, config: EntraIDConfig):
        """
        Inicializa o cliente MSAL.
        
        Args:
            config: Instância de EntraIDConfig com as credenciais
        """
        self.config = config
        
        # Inicializar a aplicação MSAL confidencial (para backend)
        self.app = msal.ConfidentialClientApplication(
            client_id=config.client_id,
            client_credential=config.client_secret,
            authority=config.authority
        )
    
    def get_auth_url(self, base_url: str, state: Optional[str] = None) -> str:
        """
        Gera a URL de autenticação para redirecionar o usuário para o Entra ID.
        
        Args:
            base_url: URL base da aplicação
            state: Parâmetro CSRF para validação (recomendado gerar aleatoriamente)
            
        Returns:
            URL completa para autenticação no Entra ID
        """
        redirect_uri = self.config.get_redirect_uri(base_url)
        
        auth_url = self.app.get_authorization_request_url(
            scopes=self.config.scopes,
            redirect_uri=redirect_uri,
            state=state
        )
        
        return auth_url
    
    def acquire_token_by_code(self, code: str, base_url: str) -> Optional[Dict[str, Any]]:
        """
        Troca o código de autorização por um token de acesso.
        
        Args:
            code: Código de autorização recebido do Entra ID
            base_url: URL base da aplicação (para calcular redirect_uri)
            
        Returns:
            Dicionário com os tokens e dados do usuário, ou None se falhar
        """
        redirect_uri = self.config.get_redirect_uri(base_url)
        
        try:
            token_response = self.app.acquire_token_by_authorization_code(
                code=code,
                scopes=self.config.scopes,
                redirect_uri=redirect_uri
            )
            
            if 'error' in token_response:
                current_app = None
                try:
                    from flask import current_app
                except Exception:
                    pass
                error_description = token_response.get('error_description', token_response.get('error', 'Erro desconhecido'))
                if current_app:
                    current_app.logger.error(f"Erro ao adquirir token: {error_description}")
                else:
                    print(f"Erro ao adquirir token: {error_description}")
                return None
            if 'id_token_claims' not in token_response and 'id_token' not in token_response:
                return None
            return token_response
        
        except Exception as e:
            print(f"Exceção ao adquirir token: {str(e)}")
            return None
    
    def get_user_info(self, token_response: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Extrai informações do usuário do token de acesso.
        
        Args:
            token_response: Resposta com tokens do Entra ID
            
        Returns:
            Dicionário com dados do usuário (name, email) ou None
        """
        if 'access_token' not in token_response:
            return None
        
        try:
            headers = {'Authorization': f"Bearer {token_response['access_token']}"}
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                user_data = response.json()
                email = user_data.get('mail') or user_data.get('userPrincipalName')
                return {
                    'id': user_data.get('id'),
                    'name': user_data.get('displayName', email or 'Usuário'),
                    'email': email,
                    'upn': user_data.get('userPrincipalName'),
                }
            else:
                current_app = None
                try:
                    from flask import current_app
                except Exception:
                    pass
                msg = f"Erro ao buscar dados do usuário: {response.status_code}"
                if current_app:
                    current_app.logger.error(msg)
                else:
                    print(msg)
                return None
        except Exception as e:
            print(f"Exceção ao buscar dados do usuário: {str(e)}")
            return None

    def get_logout_url(self, post_logout_redirect_uri: str) -> str:
        """
        Gera a URL para fazer logout no Entra ID.
        
        Args:
            post_logout_redirect_uri: URL para redirecionar após logout
            
        Returns:
            URL de logout do Entra ID
        """
        params = {
            'post_logout_redirect_uri': post_logout_redirect_uri
        }

        logout_url = f"{self.config.authority}/oauth2/v2.0/logout?{urlencode(params)}"
        return logout_url


def create_csrf_token() -> str:
    """
    Gera um token CSRF aleatório para proteger o fluxo de autenticação.
    
    Returns:
        String com token aleatório de 32 bytes em hexadecimal
    """
    return secrets.token_hex(32)


def create_or_update_user_from_entra_info(user_info: Dict[str, str]) -> Optional[User]:
    """
    Localiza o usuário existente no banco com base no e-mail retornado pelo Entra ID.

    Não cria novos usuários automaticamente. Isso garante que apenas contas já
    cadastradas no sistema possam entrar usando Entra ID.

    Args:
        user_info: Dicionário com id, email, name e upn do usuário.

    Returns:
        Instância de User ou None se o login não for autorizado.
    """
    if not user_info:
        return None

    email = (user_info.get('email') or '').strip().lower()
    if not email:
        return None

    user = User.query.filter_by(email=email).first()
    if user:
        if not user.ativo:
            return None
        if not user.email:
            user.email = email
        db.session.commit()
        return user

    user = User.query.filter_by(username=email).first()
    if user:
        if not user.ativo:
            return None
        if not user.email:
            user.email = email
        db.session.commit()
        return user

    # Não criar usuário novo automaticamente para autenticação Entra ID.
    return None


def validate_email_in_database(email: str) -> bool:
    """
    Valida se o e-mail do usuário existe no banco de dados.
    
    Esta função verifica se o email corporativo está autorizado a acessar o sistema.
    Você pode estender essa validação para também:
    - Verificar se o usuário está ativo (user.ativo == True)
    - Verificar o tipo de contrato (CLT, PJ)
    - Verificar permissões específicas de acesso
    
    Args:
        email: E-mail corporativo do usuário (geralmente do Entra ID)
        
    Returns:
        True se o email existe no banco de dados e usuário está ativo, False caso contrário
    """
    from app.models import User
    
    if not email:
        return False
    
    try:
        # Buscar usuário pelo email
        user = User.query.filter_by(email=email.strip().lower()).first()
        
        # Verificar se existe e se está ativo
        if user and user.ativo:
            return True
        
        return False
    
    except Exception as e:
        import logging
        logging.error(f"Erro ao validar email no banco de dados: {str(e)}")
        return False


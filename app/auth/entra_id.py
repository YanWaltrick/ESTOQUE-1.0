"""
Módulo de autenticação Microsoft Entra ID (Azure AD)
Integração MSAL para login único com Microsoft
"""

import json
import logging
import os
import secrets
from typing import Dict, Optional, Tuple
import msal

logger = logging.getLogger(__name__)


class EntraIDConfig:
    """Configuração do Entra ID a partir de variáveis de ambiente"""
    
    def __init__(self):
        self.client_id = os.getenv('ENTRA_CLIENT_ID')
        self.client_secret = os.getenv('ENTRA_CLIENT_SECRET')
        self.tenant_id = os.getenv('ENTRA_TENANT_ID')
        self.redirect_path = os.getenv('ENTRA_REDIRECT_PATH', '/entra-callback')
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}" if self.tenant_id else None
        
        # Validar configuração
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            logger.warning(
                "Entra ID não está completamente configurado. "
                "Verifique as variáveis: ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET, ENTRA_TENANT_ID"
            )
    
    def is_configured(self) -> bool:
        """Verifica se Entra ID está totalmente configurado"""
        return all([self.client_id, self.client_secret, self.tenant_id, self.authority])


class EntraIDClient:
    """Cliente MSAL para autenticação Microsoft Entra ID"""
    
    def __init__(self, config: EntraIDConfig, session_store: Optional[Dict] = None):
        """
        Inicializa cliente MSAL
        
        Args:
            config: EntraIDConfig com credenciais
            session_store: Dicionário de sessão para armazenar state (CSRF)
        """
        self.config = config
        self.session_store = session_store or {}
        
        if not config.is_configured():
            raise ValueError("Entra ID não está configurado. Verifique variáveis de ambiente.")
        
        # Inicializar app MSAL
        self.app = msal.ConfidentialClientApplication(
            client_id=config.client_id,
            client_credential=config.client_secret,
            authority=config.authority
        )
        
        logger.info(f"Cliente MSAL inicializado para tenant: {config.tenant_id}")
    
    def get_auth_url(self, redirect_uri: str) -> Tuple[str, str]:
        """
        Gera URL de autenticação Microsoft
        
        Args:
            redirect_uri: URI completo para callback (ex: http://localhost:5000/entra-callback)
        
        Returns:
            Tupla (auth_url, state_token) para CSRF
        """
        state = secrets.token_urlsafe(32)  # Gera state para CSRF
        
        auth_url = self.app.get_authorization_request_url(
            scopes=['User.Read'],  # Scopes mínimos para ler email
            state=state,
            redirect_uri=redirect_uri
        )
        
        # Armazenar state na sessão para validação posterior
        self.session_store['auth_state'] = state
        
        logger.debug(f"Auth URL gerada com state: {state}")
        return auth_url, state
    
    def validate_token(
        self, 
        code: str, 
        redirect_uri: str, 
        session_state: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Valida código de autorização e obtém token
        
        Args:
            code: Código de autorização do Microsoft
            redirect_uri: URI do callback (deve ser igual ao da solicitação)
            session_state: State armazenado na sessão (para CSRF)
        
        Returns:
            Dicionário com dados do token se válido, None se inválido
        """
        # Validar CSRF token (state)
        if session_state and self.session_store.get('auth_state') != session_state:
            logger.error("State mismatch - possível ataque CSRF!")
            return None
        
        try:
            # Trocar código por token
            result = self.app.acquire_token_by_authorization_code(
                code=code,
                scopes=['User.Read'],
                redirect_uri=redirect_uri
            )
            
            if 'error' in result:
                logger.error(f"Erro ao obter token: {result.get('error_description')}")
                return None
            
            logger.info("Token obtido com sucesso")
            return result
        
        except Exception as e:
            logger.error(f"Exceção ao validar token: {str(e)}")
            return None
    
    def extract_user_info(self, token_result: Dict) -> Optional[Dict]:
        """
        Extrai informações do usuário a partir do token
        
        Args:
            token_result: Resultado do acquire_token_by_authorization_code
        
        Returns:
            Dicionário com email, name, oid ou None se falhar
        """
        try:
            # Access token está em token_result['access_token']
            # ID token (com claims) está em token_result['id_token_claims']
            # ou podemos fazer uma chamada a /me endpoint
            
            if 'access_token' not in token_result:
                logger.error("Access token não encontrado no resultado")
                return None
            
            # Opção 1: Usar claims do ID token (mais rápido, sem chamada HTTP)
            if 'id_token_claims' in token_result:
                claims = token_result['id_token_claims']
                user_info = {
                    'email': claims.get('email') or claims.get('upn'),  # UPN = User Principal Name
                    'name': claims.get('name', 'Usuário Microsoft'),
                    'oid': claims.get('oid'),  # Object ID - identificador único do Entra ID
                }
                
                if user_info['email'] and user_info['oid']:
                    logger.info(f"Informações extraídas: email={user_info['email']}, oid={user_info['oid']}")
                    return user_info
            
            # Opção 2: Chamar endpoint /me (mais confiável mas necessita HTTP)
            logger.debug("ID token claims não disponível, tentando endpoint /me")
            return self._get_me_endpoint(token_result['access_token'])
        
        except Exception as e:
            logger.error(f"Erro ao extrair informações do usuário: {str(e)}")
            return None
    
    def _get_me_endpoint(self, access_token: str) -> Optional[Dict]:
        """
        Chamada ao endpoint /me do Microsoft Graph para obter info do usuário
        
        Args:
            access_token: Token de acesso
        
        Returns:
            Dicionário com userPrincipalName (email), displayName (name), id (oid)
        """
        import requests
        
        try:
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            user_info = {
                'email': data.get('userPrincipalName'),
                'name': data.get('displayName', 'Usuário Microsoft'),
                'oid': data.get('id'),
            }
            
            logger.info(f"Info do /me endpoint: email={user_info['email']}, oid={user_info['oid']}")
            return user_info
        
        except Exception as e:
            logger.error(f"Erro ao chamar /me endpoint: {str(e)}")
            return None


def create_entra_client(session_store: Optional[Dict] = None) -> Optional[EntraIDClient]:
    """
    Factory function para criar cliente Entra ID
    
    Args:
        session_store: Dicionário de sessão
    
    Returns:
        EntraIDClient se configurado, None caso contrário
    """
    config = EntraIDConfig()
    
    if not config.is_configured():
        logger.warning("Entra ID não está configurado - autenticação via Microsoft desabilitada")
        return None
    
    try:
        return EntraIDClient(config, session_store)
    except Exception as e:
        logger.error(f"Erro ao criar cliente Entra ID: {str(e)}")
        return None

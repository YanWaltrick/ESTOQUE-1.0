"""
Utilitários de validação de senha e segurança.
"""

import re
from werkzeug.security import generate_password_hash, check_password_hash


class PasswordValidator:
    """Validador de senhas com regras de complexidade."""
    
    MIN_LENGTH = 6
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = False  # Pode ativar para maior segurança
    
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    @classmethod
    def validate(cls, password: str) -> tuple[bool, list[str]]:
        """
        Valida uma senha de acordo com os critérios.
        
        Args:
            password: String com a senha a validar
            
        Retorna:
            Tupla (is_valid, list_of_errors)
            - is_valid: Boolean indicando se a senha é válida
            - list_of_errors: Lista de mensagens de erro
        """
        errors = []
        
        if not password:
            errors.append("Senha não pode estar vazia")
            return False, errors
        
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Senha deve ter no mínimo {cls.MIN_LENGTH} caracteres")
        
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Senha deve conter pelo menos uma letra maiúscula (A-Z)")
        
        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Senha deve conter pelo menos uma letra minúscula (a-z)")
        
        if cls.REQUIRE_DIGIT and not re.search(r'\d', password):
            errors.append("Senha deve conter pelo menos um número (0-9)")
        
        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
            errors.append(f"Senha deve conter pelo menos um caractere especial: {cls.SPECIAL_CHARS}")
        
        # Verificações adicionais de segurança
        if cls._is_weak_password(password):
            errors.append("Senha muito fraca ou comum. Use combinação de letras, números")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @classmethod
    def _is_weak_password(cls, password: str) -> bool:
        """Verifica se a senha é muito fraca."""
        weak_patterns = [
            r'^[a-z]+$',          # Apenas letras minúsculas
            r'^[A-Z]+$',          # Apenas letras maiúsculas
            r'^\d+$',             # Apenas números
            r'^(.)\1+$',          # Todas iguais (aaaa, 1111)
            r'^(?:123|234|345|456|567|678|789|890|abc|bcd|cde)',  # Sequências comuns
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, password):
                return True
        
        return False
    
    @classmethod
    def strength_score(cls, password: str) -> int:
        """
        Calcula um score de força da senha (0-100).
        
        Args:
            password: String com a senha
            
        Retorna:
            Integer de 0 a 100 indicando a força
        """
        score = 0
        
        # Comprimento
        if len(password) >= 6:
            score += 10
        if len(password) >= 8:
            score += 10
        if len(password) >= 12:
            score += 10
        if len(password) >= 16:
            score += 10
        
        # Tipos de caracteres
        if re.search(r'[a-z]', password):
            score += 15
        if re.search(r'[A-Z]', password):
            score += 15
        if re.search(r'\d', password):
            score += 15
        if any(c in cls.SPECIAL_CHARS for c in password):
            score += 15
        
        # Variedade
        unique_chars = len(set(password))
        score += (unique_chars / len(password)) * 10 if len(password) > 0 else 0
        
        # Penalidades
        if re.search(r'(.)\1{2,}', password):  # Caracteres repetidos 3+ vezes
            score -= 10
        
        is_valid, errors = cls.validate(password)
        if not is_valid:
            score -= 20
        
        return max(0, min(100, int(score)))  # Limitar entre 0 e 100
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """
        Hasha uma senha de forma segura.
        
        Args:
            password: String com a senha
            
        Retorna:
            String com o hash da senha
        """
        return generate_password_hash(password, method='pbkdf2:sha256')
    
    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        """
        Verifica se uma senha corresponde ao hash.
        
        Args:
            password: String com a senha
            password_hash: String com o hash armazenado
            
        Retorna:
            Boolean indicando se correspondem
        """
        return check_password_hash(password_hash, password)


def validate_username(username: str) -> tuple[bool, str]:
    """
    Valida um nome de usuário.
    
    Args:
        username: String com o nome de usuário
        
    Retorna:
        Tupla (is_valid, error_message)
    """
    if not username:
        return False, "Nome de usuário não pode estar vazio"
    
    if len(username) < 3:
        return False, "Nome de usuário deve ter no mínimo 3 caracteres"
    
    if len(username) > 150:
        return False, "Nome de usuário não pode ter mais de 150 caracteres"

    # Permite email como nome de usuário, mantendo compatibilidade com logins legados.
    if '@' in username:
        is_valid_email, email_error = validate_email(username)
        if not is_valid_email:
            return False, f"Email inválido para nome de usuário: {email_error}"
        return True, ""

    if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
        return False, "Nome de usuário só pode conter letras, números, ponto, hífen e underscore, ou ser um email válido"
    
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    """
    Valida um endereço de email (simples).
    
    Args:
        email: String com o email
        
    Retorna:
        Tupla (is_valid, error_message)
    """
    if not email:
        return False, "Email não pode estar vazio"
    
    # Regex simples para email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Email inválido"
    
    if len(email) > 150:
        return False, "Email não pode ter mais de 150 caracteres"
    
    return True, ""

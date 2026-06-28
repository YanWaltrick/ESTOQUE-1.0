# Políticas de Segurança - Sistema ESTOQUE

## Overview
Este documento descreve as práticas e mecanismos de segurança implementados no Sistema ESTOQUE.

---

## 1. Autenticação & Autorização

### Credenciais
- ✅ **Não há credenciais hard-coded**: Todas as credenciais são carregadas de variáveis de ambiente (`.env`)
- ✅ **Hashing de senhas**: Utilizamos `werkzeug.security.generate_password_hash()` com `pbkdf2:sha256`
- ✅ **Força Bruta**: Proteção contra tentativas múltiplas falhas
  - Bloqueio temporário após falhas repetidas
  - Registro de tentativas (`tentativas_login_falhas`)

### Sessões
- ✅ **Timeout por inatividade**: Usuários (não-admin) são desconectados após **10 minutos de inatividade**
- ✅ **Cookies seguros**:
  - `HttpOnly`: Impede acesso via JavaScript
  - `SameSite=Lax`: Proteção contra CSRF
  - `Secure`: HTTPS apenas (em produção)
- ✅ **CSRF Protection**: Habilitado via `Flask-WTF` em todos os formulários

### Permissões
- Dois níveis de acesso: `admin` e `usuario`
- Verificação de permissões em cada endpoint crítico
- Logs de acesso negado (403)

---

## 2. Proteção de Dados

### Database
- ✅ **Variáveis de Ambiente**: URL do banco carregada de `DATABASE_URL` (obrigatória)
- ✅ **MySQL em todos os ambientes**: mesmo dialeto em dev, teste e produção
- ✅ **Sem SQL Injection**: Uso de SQLAlchemy ORM (queries parametrizadas)

### Uploads de Arquivos
- ✅ **Validação de tipo**: Apenas `png, jpg, jpeg, gif` permitidos
- ✅ **Limite de tamanho**: Máximo 2MB por arquivo
- ✅ **Nomes seguros**: `secure_filename()` + timestamp único
- ✅ **Armazenamento**: Fora da raiz pública (`static/uploads/`)

---

## 3. Cabeçalhos de Segurança

Os seguintes cabeçalhos são adicionados automaticamente a todas as respostas:

| Cabeçalho | Valor | Propósito |
|-----------|-------|----------|
| `X-Content-Type-Options` | `nosniff` | Previne MIME sniffing |
| `X-Frame-Options` | `DENY` | Previne clickjacking (não permite iframe) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controla informações de referrer |
| `Strict-Transport-Security` | `max-age=63072000` | Força HTTPS (produção) |

---

## 4. Logging & Auditoria

### Logs Centralizados
- **Localização**: `/logs/estoque.log`
- **Rotação**: Máx 10MB por arquivo, 7 backups mantidos
- **Formato**: ISO 8601 timestamps + nível de severidade

### Eventos Registrados
- ✅ Login bem-sucedido / falho
- ✅ Logout e expiração de sessão
- ✅ Tentativas de acesso negado (403)
- ✅ Operações de banco de dados (CREATE, UPDATE, DELETE)
- ✅ Erros internos do servidor (500)
- ✅ Modificações de senha
- ✅ Upload de arquivos

### Exemplo de Log
```
2026-05-08 14:30:45 | WARNING | estoque | registrar_seguranca:75 | [AUDITORIA] usuario@example.com | UPDATE | usuarios#5 | Dados alterados
2026-05-08 14:30:46 | INFO    | estoque | set_secure_headers:92 | HTTP 200 | GET /perfil | 0.045s
```

---

## 5. Variáveis de Ambiente (Produção)

**OBRIGATÓRIAS:**
```bash
FLASK_ENV=production
SECRET_KEY=<gere-com: python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=mysql+pymysql://user:pass@host:3306/estoque_db
```

**RECOMENDADAS:**
```bash
SESSION_COOKIE_SECURE=True       # Força cookies em HTTPS
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-de-app
ADMIN_EMAILS=admin@example.com
```

**Verificação:**
```bash
# Gerar SECRET_KEY segura:
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 6. Checklist de Produção

- [ ] Defina `FLASK_ENV=production`
- [ ] Gere e configure `SECRET_KEY`
- [ ] Configure `DATABASE_URL` com credenciais seguras
- [ ] Configure `SESSION_COOKIE_SECURE=True`
- [ ] Configure SMTP para notificações de segurança
- [ ] Revise logs regularmente (`/logs/estoque.log`)
- [ ] Configure backup automático do banco de dados
- [ ] Use HTTPS/TLS (certificados válidos)
- [ ] Configure firewall (apenas portas 80/443)
- [ ] Mantenha dependências atualizadas (`pip install --upgrade -r requirements.txt`)

---

## 7. Vulnerabilidades Conhecidas & Mitigações

| Risco | Mitigação |
|-------|-----------|
| SQL Injection | ORM (SQLAlchemy) + queries parametrizadas |
| CSRF | Flask-WTF tokens em formulários |
| XSS | Jinja2 escaping automático |
| Força Bruta | Rate limiting + bloqueio temporário |
| Sessão Hijacking | HttpOnly + SameSite cookies |
| Exposição de Dados | HTTPS + headers de segurança |

---

## 8. Contato & Reporting

Para relatar vulnerabilidades de segurança:
- **Email**: seguranca@estoque.com (configure em `ADMIN_EMAILS`)
- **Não** divulgue publicamente até receber confirmação

---

**Última atualização**: Maio 2026  
**Status**: ✅ Segurança implementada

# 🔒 Sistema ESTOQUE - Início Rápido

## ⚡ Pré-requisitos
- Python 3.8+
- pip (gerenciador de pacotes Python)
- Git (opcional)

## 📦 Instalação

### 1. Clonar ou extrair o projeto
```bash
cd ESTOQUE-1.0
```

### 2. Criar ambiente virtual (recomendado)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente
Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```

**Para desenvolvimento**, o arquivo `.env` já está pré-configurado com valores seguros.

**Para produção**, atualize:
- `FLASK_ENV=production`
- `SECRET_KEY` (gere com `python -c "import secrets; print(secrets.token_hex(32))"`)
- `DATABASE_URL` (configure seu banco MySQL ou PostgreSQL)
- `SESSION_COOKIE_SECURE=True`
- Credenciais de email SMTP
- `TEAMS_CHANNEL_WEBHOOK_URL` para postar direto em um canal do Teams
- `APP_PUBLIC_BASE_URL` se quiser exibir imagens do chamado no cartão

## 🚀 Executar a Aplicação

### Desenvolvimento
```bash
python app.py
```

Acesse: http://localhost:5000

### Execução com WSGI no Windows
```bash
pip install waitress
python wsgi.py
```

Ou diretamente:
```bash
waitress-serve --listen=0.0.0.0:5000 wsgi:app
```

### Produção (Linux)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

## 👤 Login Padrão
- **Usuário**: `admin`
- **Senha**: `admin`

> ⚠️ **IMPORTANTE**: Mude a senha do admin em produção!

## 🔐 Segurança Implementada

✅ **Autenticação & Autorização**
- Hashing de senhas com PBKDF2
- Proteção contra força bruta
- Timeout de 10 minutos para usuários (não-admin)

✅ **Proteção de Dados**
- CSRF protection (Flask-WTF)
- SQL Injection prevention (ORM)
- Cookies seguros (HttpOnly, SameSite, Secure em HTTPS)
- Validação de uploads (tipos, tamanho, nome seguro)

✅ **Logging & Auditoria**
- Logs centralizados em `/logs/estoque.log`
- Rastreamento de eventos de segurança
- Rotação automática de logs (10MB max)

✅ **Cabeçalhos de Segurança**
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Strict-Transport-Security (HTTPS)
- Referrer-Policy

## 📋 Configuração de Banco de Dados

### SQLite (desenvolvimento padrão)
Nenhuma configuração necessária. O arquivo será criado em `instance/estoque.sqlite`.

### MySQL (produção)
```bash
# 1. Criar banco de dados
mysql -u root -p
mysql> CREATE DATABASE estoque_db CHARACTER SET utf8mb4;

# 2. Configurar DATABASE_URL em .env
DATABASE_URL=mysql+pymysql://usuario:senha@localhost:3306/estoque_db

# 3. Rodar app.py para inicializar tabelas
python app.py
```

## 🔔 Notificações no Teams via webhook do canal

O sistema pode enviar eventos de chamados diretamente para o webhook de um canal do Teams.

### Variáveis necessárias
- `TEAMS_CHANNEL_WEBHOOK_URL`: URL do webhook do canal no Teams.
- `POWER_AUTOMATE_WEBHOOK_URL`: mantido só para compatibilidade com integrações antigas.
- `POWER_AUTOMATE_TIMEOUT_SECONDS`: tempo máximo de espera pela resposta do webhook.
- `ADMIN_EMAILS`: lista de e-mails dos administradores que devem receber o aviso.
- `APP_PUBLIC_BASE_URL`: URL pública da aplicação, usada para imagens no cartão do Teams.

### Eventos enviados
- Criação de chamado.
- Alteração de status do chamado.

### Payload
O backend envia um cartão do Teams com os dados do chamado, usuário solicitante, status atual, status anterior e anexo quando houver URL pública disponível.

## 📁 Estrutura de Diretórios

```
ESTOQUE-1.0/
├── app/
│   ├── __init__.py          # Factory + logging + error handlers
│   ├── database.py          # Configuração do SQLAlchemy + SESSION
│   ├── models/              # Modelos de dados
│   ├── routes/              # Blueprints (auth, main, admin, api)
│   ├── auth/                # Autenticação + permissões
│   ├── services/            # Lógica de negócio
│   └── utils/
│       └── logger.py        # Sistema de logging centralizado
├── instance/                # BD SQLite (gerado automaticamente)
├── logs/                    # Logs de aplicação (gerado automaticamente)
├── templates/               # HTML Jinja2
├── static/                  # CSS, JS, imagens, uploads
├── migrations/              # Migrações de banco (Flask-Migrate)
├── .env                     # Variáveis de ambiente (criar do .env.example)
├── .env.example             # Exemplo de configuração
├── app.py                   # Ponto de entrada
├── requirements.txt         # Dependências Python
└── SECURITY.md              # Documentação de segurança
```

## 🔍 Verificação de Saúde

### Testar imports e inicialização
```bash
python -c "from app import create_app; app = create_app(); print('OK')"
```

### Verificar logs
```bash
tail -f logs/estoque.log  # macOS/Linux
Get-Content logs/estoque.log -Tail 20  # Windows PowerShell
```

## 📊 Verificação de Dependências

### Auditoria de segurança
```bash
pip install pip-audit
pip-audit
```

### Listar pacotes instalados
```bash
pip freeze
```

## ❓ Troubleshooting

### Erro: `SECRET_KEY não definida`
Verifique se `.env` existe e contém `SECRET_KEY`.

### Erro: `unable to open database file`
- Verifique permissões da pasta `instance/`
- Confirme que `DATABASE_URL` em `.env` usa caminho válido

### Erro: `CSRF token missing`
Adicione `{{ csrf_token() }}` em formulários HTML:
```html
<form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />
    ...
</form>
```

### Erro: `Module not found`
Reinstale dependências:
```bash
pip install -r requirements.txt --force-reinstall
```

## 📞 Contato & Support

Para relatar vulnerabilidades de segurança:
- Configure `ADMIN_EMAILS` em `.env`
- Relatórios enviados via SMTP (configure `MAIL_*`)

---

**Última atualização**: Maio 2026  
**Status**: ✅ Pronto para produção

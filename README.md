# Sistema ESTOQUE

Este projeto hoje funciona como uma aplicação web em Flask para gestão de estoque, usuários, chamados (tickets), documentos e termos de entrega. O fluxo principal é baseado em autenticação local.

## Como o sistema funciona hoje

### 1. Autenticação e acesso
- O sistema possui login local com usuário e senha.
- Há fluxo de recuperação de senha, reautenticação para alterar dados sensíveis e upload de foto de perfil.
- Usuários podem ser administradores ou usuários comuns.
- A sessão de usuários não-administradores expira após 10 minutos de inatividade.

### 2. Gestão de usuários
- Administradores podem criar, editar, ativar/desativar e listar usuários.
- O cadastro suporta dois tipos de contrato: CLT e PJ.
- Há campos específicos para dados cadastrais, área, localização, empresa, CPF/CNPJ e dados de contrato PJ.
- Ao criar um usuário, o sistema gera automaticamente um Termo de Entrega e Responsabilidade.

### 3. Controle de estoque
- Os produtos são gerenciados pelo módulo de estoque.
- É possível criar, editar, remover, listar e movimentar produtos.
- O sistema registra entradas e saídas com histórico de movimentações.
- Há relatórios de estoque baixo, valor total do estoque e consolidação por categoria.

### 4. Chamados / tickets
- O sistema também funciona como um canal de solicitação de chamados (chamadas).
- Usuários podem abrir e acompanhar chamados, enquanto administradores acompanham e atualizam o status.
- O fluxo pode disparar notificações por e-mail e por webhook para Microsoft Teams/Power Automate.
- O sistema registra eventos e auditoria para ações importantes.

### 5. Documentos e termos
- Administradores podem enviar documentos empresariais para usuários específicos.
- Usuários podem baixar e visualizar os documentos disponíveis para si.
- Há suporte a upload de arquivos com validação de tipo e tamanho.
- Termos de entrega e responsabilidade são associados aos usuários.

## Requisitos
- Python 3.10+ (recomendado)
- pip
- Git (opcional)

## Instalação

### 1. Entrar na pasta do projeto
```bash
cd ESTOQUE-1.0
```

### 2. Criar ambiente virtual
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente
Crie um arquivo `.env` com as configurações necessárias. O projeto usa variáveis como:
- `SECRET_KEY`
- `FLASK_ENV`
- `DATABASE_URL` (opcional; se não for informado, o sistema usa SQLite local)
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`
- `ADMIN_EMAILS`
- `TEAMS_CHANNEL_WEBHOOK_URL`
- `POWER_AUTOMATE_WEBHOOK_URL`
- `APP_PUBLIC_BASE_URL`

Se necessário, copie o exemplo existente para a raiz do projeto e ajuste os valores.

## Execução

### Rodar em desenvolvimento
```bash
python app.py
```

A aplicação fica disponível em:
```text
http://localhost:5000
```

### Rodar com WSGI
```bash
python wsgi.py
```

## Usuário inicial
Ao iniciar a aplicação pela primeira vez, se não existir um usuário administrador, o sistema cria automaticamente:
- usuário: `admin`
- senha: `admin`

> Recomendação: altere a senha do usuário admin logo após a primeira instalação.

## Estrutura principal do projeto
```text
app/
  __init__.py          # fábrica da aplicação, blueprints, segurança e inicialização
  database.py         # configuração do banco e email
  routes/             # rotas de login, admin, API, documentos e autenticação Entra ID
  services/           # lógica do estoque e notificações
  models/             # modelos de usuários, produtos, movimentações, chamados e documentos
static/               # CSS, JavaScript, uploads e arquivos estáticos
templates/            # páginas HTML renderizadas pelo Flask
migrations/           # migrações do banco
```

## Pontos importantes do funcionamento atual
- O ponto de entrada principal é [app.py](app.py).
- A aplicação é montada pela função `create_app()` em [app/__init__.py](app/__init__.py).
- O estoque é controlado pelo serviço em [app/services/estoque_service.py](app/services/estoque_service.py).
- As rotas principais estão em [app/routes/main.py](app/routes/main.py), [app/routes/admin.py](app/routes/admin.py), [app/routes/api.py](app/routes/api.py) e [app/routes/auth.py](app/routes/auth.py).

## Observações
- O projeto usa SQLAlchemy e Flask-Login.
- O banco pode ser SQLite no ambiente local ou MySQL/PostgreSQL conforme configuração.
- Logs e eventos são registrados durante login, operações de estoque, upload de documentos, alterações de status e outras ações relevantes.
- Uploads de arquivos são salvos em pastas da aplicação sob o diretório de static.

## Status
- O sistema está em funcionamento como uma aplicação web completa para gestão operacional interna.
- A documentação abaixo foi atualizada para refletir o funcionamento atual do projeto.

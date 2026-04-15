# Sistema de Estoque

Sistema empresarial de gerenciamento de estoque desenvolvido com Flask, SQLAlchemy, SQLite/MySQL e RBAC.

**✨ Recursos principais:**
- 🔐 **Autenticação segura** com proteção contra força bruta
- 👥 **RBAC** (Role-Based Access Control) com 4 níveis de acesso
- 📊 **Gestão de estoque** completa com entrada/saída
- 📈 **Relatórios** de movimentação
- 🔍 **Auditoria** de todas as ações
- 🐳 **Containerização** com Docker
- 🗄️ **Controle de versão** de banco de dados com Flask-Migrate

## Arquitetura

O projeto foi reestruturado seguindo o padrão **Application Factory** do Flask, organizando o código em camadas para melhor manutenção e escalabilidade.

### Estrutura de Diretórios

```
app/
├── __init__.py          # Application Factory
├── database.py          # Configuração do banco de dados
├── migrate.py           # Configuração do Flask-Migrate
├── auth/                # Autenticação e RBAC
│   ├── __init__.py
│   ├── decorators.py    # Decoradores @require_role, @require_permission
│   └── security.py      # Validação de senha, hashing
├── models/              # Definições dos modelos de dados
│   └── __init__.py
├── routes/              # Rotas organizadas em Blueprints
│   ├── __init__.py
│   ├── auth.py          # Rotas de autenticação (login, perfil)
│   ├── main.py          # Rotas principais (index, admin)
│   ├── admin.py         # Rotas administrativas (gestão de usuários)
│   └── api.py           # API REST (produtos, movimentações, relatórios)
├── services/            # Lógica de negócio
│   ├── __init__.py
│   └── estoque_service.py  # EstoqueService
└── utils/               # Utilitários
    └── __init__.py      # registrar_evento
```

### Camadas

- **Models**: Definem a estrutura dos dados (User, Produto, Movimentacao, etc.)
- **Auth**: Autenticação segura com RBAC, validação de senhas
- **Services**: Contêm a lógica de negócio (operações de estoque, validações)
- **Routes**: Organizam as rotas em Blueprints (auth, main, admin, api)
- **Utils**: Funções auxiliares (registro de eventos)

## Segurança 🔒

O sistema implementa **RBAC com 4 níveis de acesso**:

| Role | Permissões |
|------|-----------|
| **admin** | Acesso completo, deletar usuários, gerenciar tudo |
| **gerente** | Criar/editar produtos, criar usuários, relatórios |
| **operador** | Registrar entrada/saída, visualizar estoque |
| **usuario** | Visualizar estoque, criar chamados |

**Proteções implementadas:**
- ✅ Hash PBKDF2-SHA256 para senhas
- ✅ Validação de força de senha (maiúscula, minúscula, número)
- ✅ Proteção contra força bruta (bloqueio após 5 tentativas)
- ✅ Auditoria completa de acessos e ações
- ✅ Decoradores RBAC para proteção de rotas
- ✅ Proteção contra open redirect attacks

**Leia:** [RBAC_GUIDE.md](./RBAC_GUIDE.md) para documentação completa

## Instalação e Execução

### Opção 1: Tradicional (Python Local)

1. Instalar dependências:
```bash
pip install -r requirements.txt
```

2. Inicializar o banco de dados:
```bash
python init_db_simple.py
```

3. Executar a aplicação:
```bash
python app.py
```

A aplicação estará disponível em `http://127.0.0.1:5000`

**Login padrão:**
- Usuário: `admin`
- Senha: `Admin@123`

### Opção 2: Docker (Recomendado) 🐳

Docker torna tudo simples e funciona em qualquer computador!

**Pré-requisito:** Instalar [Docker Desktop](https://www.docker.com/products/docker-desktop)

1. Build é execução:
```bash
docker-compose up
```

Pronto! A aplicação estará em `http://localhost:5000`

**Mais comandos Docker:**
```bash
docker-compose up -d        # Executar em background
docker-compose logs -f      # Ver logs em tempo real
docker-compose down         # Parar containers
docker-compose exec flask-app bash  # Entrar no container
```

Para mais detalhes, veja [DOCKER_GUIDE.md](./DOCKER_GUIDE.md)

## Dados de Acesso Padrão

- **Usuário**: admin
- **Senha**: admin

## Funcionalidades

- **Autenticação**: Login/logout, mudança de senha
- **Gerenciamento de Produtos**: CRUD completo
- **Controle de Estoque**: Entrada/saída de produtos
- **Relatórios**: Estatísticas e relatórios de estoque
- **Administração**: Gerenciamento de usuários
- **Histórico**: Auditoria de todas as operações

## API REST

### Produtos
- `GET /api/produtos` - Listar todos os produtos
- `GET /api/produtos/<id>` - Obter produto específico
- `POST /api/produtos` - Criar novo produto
- `PUT /api/produtos/<id>` - Atualizar produto
- `DELETE /api/produtos/<id>` - Remover produto

### Movimentações
- `POST /api/entrada` - Registrar entrada de estoque
- `POST /api/saida` - Registrar saída de estoque

### Relatórios
- `GET /api/relatorios/resumo` - Resumo do estoque

## Banco de Dados

O sistema suporta MySQL e SQLite. Por padrão, usa SQLite para simplicidade.

Para usar MySQL, configure a variável `DATABASE_URL` no arquivo `.env`:

```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/database_name
```

## Flask-Migrate (Versionamento de Banco de Dados)

O projeto usa **Flask-Migrate** para gerenciar mudanças no schema do banco de dados de forma profissional.

### Comandos Úteis

```bash
# Ver versao atual do banco
python manage.py db current

# Ver historico completo de migracoes
python manage.py db history

# Criar nova migracao
python manage.py db migrate -m "Descricao da mudanca"

# Aplicar migracoes
python manage.py db upgrade

# Reverter ultima migracao
python manage.py db downgrade
```

### Rápida Recuperação de Desastres

Se o banco de dados inteiro for deletado:

```bash
python manage.py db upgrade
```

Pronto! O banco será recriado com todas as tabelas em segundos.

Para mais detalhes, consulte [MIGRATIONS_GUIDE.md](MIGRATIONS_GUIDE.md).

## Desenvolvimento

O projeto segue boas práticas de desenvolvimento Flask:
- Application Factory Pattern
- Blueprints para organização de rotas
- Separação clara entre camadas (Models, Services, Routes)
- SQLAlchemy para ORM
- Flask-Login para autenticação
- Flask-Mail para notificações por email
- Flask-Migrate para versionamento do banco de dados
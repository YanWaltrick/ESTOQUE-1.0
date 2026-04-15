# 🏗️ Arquitetura do Projeto ESTOQUE

## Visão Geral

O projeto segue o padrão **Application Factory** do Flask com arquitetura em camadas.

```
ESTOQUE/
├── app/                              # Núcleo da aplicação
│   ├── __init__.py                   # Application Factory (create_app)
│   ├── database.py                   # Configuração SQLAlchemy
│   ├── migrate.py                    # Flask-Migrate initialization
│   ├── models/                       # Camada de dados
│   │   └── __init__.py               # Todas as 6 entidades
│   ├── routes/                       # Blueprints (rotas)
│   │   ├── auth.py                   # Autenticação e perfil
│   │   ├── main.py                   # Página inicial e admin
│   │   ├── admin.py                  # Funções admin
│   │   └── api.py                    # API REST para integração
│   ├── services/                     # Lógica de negócio
│   │   └── estoque_service.py        # Classe EstoqueService
│   └── utils/                        # Utilitários
│       └── __init__.py               # Função registrar_evento
├── templates/                        # HTML (Jinja2)
├── static/                           # CSS, JS, imagens
├── migrations/                       # Versionamento de DB (Alembic)
├── instance/                         # Banco de dados local
│   └── estoque.db                    # SQLite (criado automaticamente)
├── app.py                            # Entry point simples
├── requirements.txt                  # Dependências Python
├── manage.py                         # CLI para Flask-Migrate
├── init_db_simple.py                 # Setup inicial do banco
├── setup_migrations.py               # Setup avançado (com Migrate)
├── .env                              # Variáveis de ambiente
├── Dockerfile                        # Container Docker
├── docker-compose.yml                # Orquestração local
├── docker-compose.prod.yml           # Orquestração produção
├── .dockerignore                     # Arquivos ignorados no build
└── entrypoint.sh                     # Script de iniciação container
```

---

## Componentes Principais

### 1️⃣ Modelos de Dados (`app/models/__init__.py`)

**6 entidades principais:**

| Tabela | Propósito | Colunas Principais |
|--------|-----------|-------------------|
| **users** | Autenticação e autorização | id, username, password_hash, role, area |
| **produtos** | Itens em estoque | id_produto, nome, categoria, quantidade, preço |
| **movimentacoes** | Histórico de entrada/saída | id_movimentacao, id_produto, tipo, quantidade, data |
| **categorias** | Classificação de produtos | id_categoria, nome, descricao |
| **chamadas** | Sistema de tickets/mensagens | id_chamada, id_usuario, mensagem, status |
| **historico** | Auditoria de eventos | id_evento, tipo_evento, usuario_responsavel, data |

**Relacionamentos:**
```
users ←→ chamadas (1:N)
usuarios ←→ movimentacoes (1:N)
produtos ←→ movimentacoes (1:N)
produtos → categorias (N:1)
```

---

### 2️⃣ Rotas (Blueprints em `app/routes/`)

#### `auth.py` - Autenticação
- `POST /login` - Login de usuário
- `GET /logout` - Logout
- `GET /perfil` - Perfil do usuário logado
- `POST/GET /forgot_password` - Recuperação de senha

#### `main.py` - Página Principal
- `GET /` - Dashboard/Índice
- `GET /admin` - Painel administrativo

#### `admin.py` - Funções Admin
- Gerenciamento de usuários (placeholder para extensão)

#### `api.py` - REST API
- `GET /api/produtos` - Lista todos os produtos
- `POST /api/produtos` - Cria novo produto
- `PUT /api/produtos/<id>` - Atualiza produto
- `DELETE /api/produtos/<id>` - Deleta produto
- `POST /api/movimentacoes` - Registra entrada/saída
- `GET /api/relatorios` - Relatórios de movimentação

---

### 3️⃣ Serviços (`app/services/estoque_service.py`)

**EstoqueService** - Lógica de negócio centralizada:
- `adicionar_produto()` - Novo item ao estoque
- `registrar_entrada()` - Entrada de mercadoria
- `registrar_saida()` - Saída de mercadoria
- `get_quantidade()` - Quantidade atual
- `verificar_minimo()` - Alerta se abaixo do mínimo
- `gerar_relatorio()` - Relatório consolidado

**Vantagem:** Todas as regras de negócio em um lugar, fácil de testar.

---

### 4️⃣ Banco de Dados

#### SQLite (Padrão Local)
```
DATABASE_URL = sqlite:///estoque.db
Localização: instance/estoque.db
Vantagem: Sem servidor externo, perfeito para desenvolvimento
```

#### MySQL (Produção)
```
DATABASE_URL = mysql+pymysql://user:pass@host:3306/estoque
Configurar em .env
```

#### Gerenciamento com Flask-Migrate
```bash
# Ver versão atual
python manage.py db current

# Criar migration (após modificar modelos)
python manage.py db migrate -m "Descrição da mudança"

# Aplicar migrations
python manage.py db upgrade

# Reverter última migration
python manage.py db downgrade
```

---

### 5️⃣ Docker

**Desenvolvimento (`docker-compose.yml`):**
```yaml
Services: flask-app (Python 3.11)
Ports: 127.0.0.1:5000
BD: SQLite no volume ./instance
Modo: Auto-reload ativado
```

**Produção (`docker-compose.prod.yml`):**
```yaml
Services: flask-app (otimizado)
Healthcheck: ✓ ativo
Restart: Automático
BD: MySQL configurável
```

---

## Fluxo de Requisição

```
Navegador (http://localhost:5000)
    ↓
app.py (entry point)
    ↓
create_app() (Application Factory)
    ↓
routes/ (Blueprint - auth.py, main.py, etc)
    ↓
services/ (EstoqueService - lógica)
    ↓
models/ (SQLAlchemy ORM)
    ↓
database.py (SQLAlchemy + db connection)
    ↓
instance/estoque.db ou MySQL
```

---

## Como Estender o Projeto

### ➕ Adicionar Nova Rota
1. Editar `app/routes/[arquivo].py` ou criar novo
2. Criar função com `@bp.route('/caminho')`
3. Registrar blueprint em `app/__init__.py` se novo arquivo

### ➕ Adicionar Novo Modelo
1. Editar `app/models/__init__.py`
2. Criar classe que herda de `db.Model`
3. Criar migration:
   ```bash
   python manage.py db migrate -m "Adicionar tabela X"
   python manage.py db upgrade
   ```

### ➕ Adicionar Lógica de Negócio
1. Adicionar método em `app/services/estoque_service.py`
2. Chamar em `app/routes/api.py`
3. Testar com requisição HTTP

---

## Configurações

**`.env` - Variáveis de Ambiente:**
```env
FLASK_ENV=development
FLASK_APP=app.py
DATABASE_URL=sqlite:///estoque.db
SECRET_KEY=sua_chave_secreta_aqui
```

**`app/database.py` - Configuração SQLAlchemy:**
```python
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'sqlite:///estoque.db'
)
```

---

## Relacionamentos das Tabelas

```sql
-- users (autenticação)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20),          -- admin, gerente, operador
    area VARCHAR(100),
    localizacao VARCHAR(100),
    data_criacao DATETIME
);

-- produtos (estoque)
CREATE TABLE produtos (
    id_produto INTEGER PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    categoria_id INTEGER,
    preco FLOAT,
    quantidade INTEGER DEFAULT 0,
    minimo INTEGER,
    localizacao VARCHAR(100),
    data_criacao DATETIME,
    data_atualizacao DATETIME,
    FOREIGN KEY(categoria_id) REFERENCES categorias(id_categoria)
);

-- movimentacoes (histórico)
CREATE TABLE movimentacoes (
    id_movimentacao INTEGER PRIMARY KEY,
    id_produto INTEGER NOT NULL,
    tipo VARCHAR(20),          -- entrada, saida
    quantidade INTEGER,
    motivo VARCHAR(255),
    data_movimentacao DATETIME,
    usuario VARCHAR(80),
    FOREIGN KEY(id_produto) REFERENCES produtos(id_produto)
);

-- categorias
CREATE TABLE categorias (
    id_categoria INTEGER PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    data_criacao DATETIME
);

-- chamadas (tickets/mensagens)
CREATE TABLE chamadas (
    id_chamada INTEGER PRIMARY KEY,
    id_usuario INTEGER,
    mensagem TEXT,
    data_criacao DATETIME,
    lida BOOLEAN,
    status VARCHAR(20),        -- aberta, em_progresso, fechada
    FOREIGN KEY(id_usuario) REFERENCES users(id)
);

-- historico (auditoria)
CREATE TABLE historico (
    id_evento INTEGER PRIMARY KEY,
    tipo_evento VARCHAR(100),
    descricao TEXT,
    usuario_responsavel VARCHAR(80),
    data_evento DATETIME,
    detalhes TEXT
);
```

---

## Stack Tecnológico

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| **Backend** | Flask | 3.1.3 |
| **ORM** | SQLAlchemy | 2.0.48 |
| **Autenticação** | Flask-Login | 0.6.3 |
| **Migração DB** | Flask-Migrate | 4.0.5 |
| **Email** | Flask-Mail | 0.10.0 |
| **BD Local** | SQLite | nativa |
| **BD Produção** | MySQL | 5.7+ |
| **Containerização** | Docker | latest |
| **Python** | 3.11 | mínimo requerido |

---

## Boas Práticas Implementadas

✅ **Application Factory** - Múltiplas instâncias da app possíveis
✅ **Blueprints** - Rotas organizadas e modulares
✅ **Separação de Responsabilidades** - Models, Routes, Services em pastas
✅ **Migrations** - Versionamento de banco de dados
✅ **Docker** - Ambiente idêntico dev/prod
✅ **Environment Variables** - Configurações seguras
✅ **Error Handling** - Tratamento de exceções centralizado
✅ **Auditoria** - Histórico de eventos em tabela dedicada

---

## Próximas Melhorias Sugeridas

- 📊 Dashboard consolidado com gráficos (Chart.js)
- 🔐 Autenticação OAuth2 / LDAP
- 📧 Notificações por email
- 🔔 WebSockets para real-time updates
- 📱 API Mobile (React Native/Flutter)
- ☁️ Deploy em Kubernetes
- 🧪 Testes automatizados (pytest)
- 📈 Analytics e BI

---

**Último documento atualizado:** 2024
**Versão da Arquitetura:** 2.0 (Application Factory + Docker)

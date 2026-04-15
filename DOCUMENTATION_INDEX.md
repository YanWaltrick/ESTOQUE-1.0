# 📚 Documentação - Sistema de Estoque

Bem-vindo! Este projeto está completamente documentado. Escolha seu ponto de entrada abaixo:

---

## 🚀 QUERO COMEÇAR AGORA!

**→ Leia em 30 segundos:** [QUICKSTART.md](./QUICKSTART.md)

```bash
# Com Docker
docker-compose up

# Ou sem Docker
pip install -r requirements.txt
python init_db_simple.py
python app.py
```

---

## 📖 Navegação por Tópico

### Para Iniciantes
1. [QUICKSTART.md](./QUICKSTART.md) - Começar em 30s
2. [README.md](./README.md) - Visão geral do projeto
3. [ARCHITECTURE.md](./ARCHITECTURE.md) - Entender a estrutura

### Para Desenvolvedores
1. [ARCHITECTURE.md](./ARCHITECTURE.md) - Stack e padrões usados
2. [RBAC_GUIDE.md](./RBAC_GUIDE.md) - Autenticação e Autorização
3. [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) - Usar Docker localmente
4. [MIGRATIONS_GUIDE.md](./MIGRATIONS_GUIDE.md) - Gerenciar banco de dados

### Para DevOps / Deploy
1. [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) - Seção "Deployment"
2. [ARCHITECTURE.md](./ARCHITECTURE.md) - Configurações de produção
3. `docker-compose.prod.yml` - Arquivo de orquestração produção

### Para DBA / Banco de Dados
1. [MIGRATIONS_GUIDE.md](./MIGRATIONS_GUIDE.md) - Controle de versão de BD
2. [ARCHITECTURE.md](./ARCHITECTURE.md) - Seção "Modelo de Dados"
3. `app/models/__init__.py` - Código dos modelos

### Para Administradores de Sistema
1. [RBAC_GUIDE.md](./RBAC_GUIDE.md) - Gerenciamento de usuários e permissões
2. [QUICKSTART.md](./QUICKSTART.md) - Deploy e configuração inicial
3. [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) - Containerização

---

## 📄 Arquivos de Documentação

| Arquivo | Tempo Leitura | Para Quem | Conteúdo |
|---------|---------------|-----------|----------|
| [QUICKSTART.md](./QUICKSTART.md) | 2 min | Todos | Como começar em 30 segundos |
| [README.md](./README.md) | 5 min | Todos | Visão geral, features, requisitos |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 10 min | Devs | Stack, modelos, padrões de código |
| [RBAC_GUIDE.md](./RBAC_GUIDE.md) | 15 min | Todos | Autenticação, Autorização, Segurança |
| [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) | 15 min | Devs/DevOps | Docker, docker-compose, deploy |
| [MIGRATIONS_GUIDE.md](./MIGRATIONS_GUIDE.md) | 10 min | DBAs/Devs | Flask-Migrate, versionamento de BD |

---

## 🔍 Índice de Conteúdo

### QUICKSTART.md
- Começar sem Docker
- Começar com Docker
- Credenciais padrão
- Troubleshooting rápido

### README.md
- Descrição do projeto
- Features principais
- Requisitos do sistema
- Instalação (2 opções)
- Estrutura de pastas
- Tabelas do banco

### ARCHITECTURE.md
- Organização de pastas
- Componentes principais (modelos, rotas, serviços)
- Blueprints e roteamento
- Stack tecnológico
- Fluxo de requisição
- Como estender o projeto
- Boas práticas implementadas
- Melhorias sugeridas

### DOCKER_GUIDE.md
- Por que Docker
- Instalação
- Primeiros passos
- Comandos úteis
- Desenvolvimento local
- MySQL (opcional)
- Troubleshooting
- Deployment (Docker Hub, Railway, Render, etc)

### MIGRATIONS_GUIDE.md
- O que é Flask-Migrate
- Como funciona
- Primeiros passos
- Criar migrations
- Aplicar migrations
- Reverter mudanças
- Produção
- Troubleshooting

---

## 🎯 Cenários Comuns

### ❓ "Quero começar a usar o app agora"
→ [QUICKSTART.md](./QUICKSTART.md)

### ❓ "Quero usar Docker"
→ [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) > Seção "Primeiros passos"

### ❓ "Como funciona a autenticação e segurança?"
→ [RBAC_GUIDE.md](./RBAC_GUIDE.md) > Seção "Visão Geral"

### ❓ "Como criar ou permitir que alguém acesse o sistema?"
→ [RBAC_GUIDE.md](./RBAC_GUIDE.md) > Seção "Gerenciamento de Usuários"

### ❓ "Preciso atribuir permissões diferentes a usuários"
→ [RBAC_GUIDE.md](./RBAC_GUIDE.md) > Seção "Permissões por Role"

### ❓ "Quero adicionar uma tabela ao banco"
→ [MIGRATIONS_GUIDE.md](./MIGRATIONS_GUIDE.md) > Seção "Criar Migrations"

### ❓ "Quero entender a estrutura do código"
→ [ARCHITECTURE.md](./ARCHITECTURE.md) > Seção "Componentes Principais"

### ❓ "Quero fazer deploy em produção"
→ [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) > Seção "Deployment"

### ❓ "Quero resetar o banco de dados"
→ [QUICKSTART.md](./QUICKSTART.md) > Seção "Problemas" OU [MIGRATIONS_GUIDE.md](./MIGRATIONS_GUIDE.md)

### ❓ "Recebi um erro, como faço debug?"
→ Procure por "Troubleshooting" em [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) ou [QUICKSTART.md](./QUICKSTART.md)

### ❓ "Como adicionar uma nova rota?"
→ [ARCHITECTURE.md](./ARCHITECTURE.md) > Seção "Como Estender o Projeto"

### ❓ "Minha conta foi bloqueada por múltiplas tentativas"
→ [RBAC_GUIDE.md](./RBAC_GUIDE.md) > Seção "Troubleshooting"

### ❓ "Quero ver quem fez o quê e quando"
→ [RBAC_GUIDE.md](./RBAC_GUIDE.md) > Seção "Eventos de Auditoria"

---

## 🗂️ Estrutura Rápida

```
/
├── QUICKSTART.md          ← COMECE AQUI
├── README.md              ← Depois aqui
├── ARCHITECTURE.md        ← Entender a estrutura
├── DOCKER_GUIDE.md        ← Se usar Docker
├── MIGRATIONS_GUIDE.md    ← Se modificar BD
│
├── app/                   ← Código da aplicação
│   ├── __init__.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
│
├── templates/             ← HTML
├── static/                ← CSS, JS, imagens
├── migrations/            ← Versionamento BD
│
├── Dockerfile             ← Container
├── docker-compose.yml     ← Dev com Docker
├── docker-compose.prod.yml ← Prod com Docker
└── requirements.txt       ← Dependências
```

---

## 💡 Dicas Importantes

✅ **Leia QUICKSTART primeiro** - Leva 2 minutos  
✅ **use Docker** - Uma linha de comando (`docker-compose up`)  
✅ **Não modifique migrations manualmente** - Use `python manage.py db migrate`  
✅ **Credenciais padrão** - user: `admin`, pass: `admin`  
✅ **Encontrou bug?** - Verifique TROUBLESHOOTING nos docs relevantes  

---

## 📞 Suporte Rápido

### "Não funciona meu venv"
→ Use Docker! [DOCKER_GUIDE.md](./DOCKER_GUIDE.md)

### "Banco de dados corrompido"
→ Delete `instance/estoque.db` e rode `python init_db_simple.py`

### "Container não inicia"
→ [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) > Troubleshooting

### "Preciso restaurar backup"
→ [MIGRATIONS_GUIDE.md](./MIGRATIONS_GUIDE.md) > Produção

---

## 📊 Sumário Gráfico

```
┌─────────────────────────────────────────┐
│  Novo no Projeto?                       │
│  ↓                                      │
│  QUICKSTART.md (2 min)                  │
│  ↓                                      │
│  README.md (5 min)                      │
│  ↓                                      │
│  ARCHITECTURE.md (10 min)               │
│  ↓                                      │
│  Pronto para desenvolver!               │
└─────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  Precisa de ajuda específica?            │
│                                          │
│  Docker → DOCKER_GUIDE.md                │
│  BD/Migrations → MIGRATIONS_GUIDE.md     │
│  Código → ARCHITECTURE.md                │
│  Começar → QUICKSTART.md                 │
└──────────────────────────────────────────┘
```

---

## 📝 Histórico de Documentação

| Data | Arquivo | O que foi adicionado |
|------|---------|---------------------|
| 2024 | README.md | Documentação base |
| 2024 | MIGRATIONS_GUIDE.md | Flask-Migrate e versionamento BD |
| 2024 | DOCKER_GUIDE.md | Containerização e Deploy |
| 2024 | ARCHITECTURE.md | Estrutura de código e padrões |
| 2024 | QUICKSTART.md | Início rápido |
| 2024 | DOCUMENTATION_INDEX.md | Este arquivo |

---

**Pronto para começar?** 🚀

**→ [QUICKSTART.md](./QUICKSTART.md)**

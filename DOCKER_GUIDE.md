# Docker Guide - Sistema de Estoque

## Por Que Usar Docker?

**Problema Anterior:**
- ModuleNotFoundError: `flask_migrate` não encontrado
- Python versão diferente em cada máquina
- XAMPP perdendo dados
- Código funciona no seu PC mas não em outro

**Solução com Docker:**
- 🐳 Tudo empacotado em um container
- ✅ Funciona igual em qualquer computador
- 🔒 Isolamento completo do sistema
- 📦 Sem instalar nada a mais (só Docker)
- ⚡ Setup em segundos

## Pré-requisitos

### Instalação do Docker

#### Windows/Mac
Baixe e instale: https://www.docker.com/products/docker-desktop

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER
```

**Verificar instalação:**
```bash
docker --version
docker-compose --version
```

## Estrutura do Projeto

```
ESTOQUE-1.0/
├── Dockerfile           # Imagem da aplicação
├── docker-compose.yml   # Orquestração
├── .dockerignore        # Arquivos ignorados
├── app/                 # Código da aplicação
├── templates/           # Templates HTML
├── static/              # Arquivos estáticos
├── migrations/          # Migrações do banco
├── requirements.txt     # Dependências Python
└── app.py               # Arquivo principal
```

## Primeiros Passos

### 1. Build da Imagem

```bash
# Construir imagem Docker
docker-compose build

# Ou apenas
docker build -t estoque-app .
```

Isso irá:
- Baixar imagem Python 3.11
- Instalar dependências do sistema
- Instalar pacotes Python (requirements.txt)
- Preparar o container

### 2. Iniciar a Aplicação

```bash
# Iniciar container em foreground (ver logs)
docker-compose up

# Ou iniciar em background
docker-compose up -d
```

**Pronto!** A aplicação estará em: `http://localhost:5000`

### 3. Acessar a Aplicação

```
URL: http://localhost:5000
Usuário: admin
Senha: admin
```

## Comandos Úteis

### Iniciar/Parar

```bash
# Iniciar containers
docker-compose up

# Iniciar em background
docker-compose up -d

# Parar containers
docker-compose down

# Parar e remover volumes
docker-compose down -v
```

### Ver Logs

```bash
# Ver logs em tempo real
docker-compose logs -f

# Ver logs do serviço específico
docker-compose logs flask-app

# Últimas linhas
docker-compose logs --tail=100
```

### Executar Comandos

```bash
# Entrar no shell do container
docker-compose exec flask-app bash

# Executar comando específico
docker-compose exec flask-app python manage.py db history

# Inicializar banco do zero
docker-compose exec flask-app python init_db_simple.py
```

### Gerenciar Dados

```bash
# Ver volumes criados
docker volume ls

# Remover todos os volumes
docker volume prune

# Backup do banco SQLite
docker cp estoque-app:/app/instance/estoque.db ./backup.db
```

## Desenvolvimento com Docker

### Workflow de Desenvolvimento

1. **Edite o código** normalmente no seu editor
2. **O container detecta mudanças** (se usando volumes)
3. **Recarregue o navegador** para ver as mudanças

```bash
# Iniciar com reload automático
docker-compose up
```

### Flask Debugger

O Flask debugger fica ativo. Se encontrar erro, verá direto no navegador.

### Instalar Novo Pacote

Adicione ao `requirements.txt`:

```
novo-pacote==1.0.0
```

Depois rebuild e restart:

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

## Usando Com MySQL (Opcional)

### 1. Descomentar MySQL no docker-compose.yml

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: senha123
      MYSQL_DATABASE: estoque_db

  flask-app:
    environment:
      - DATABASE_URL=mysql+pymysql://root:senha123@mysql:3306/estoque_db
    depends_on:
      - mysql
```

### 2. Iniciar

```bash
docker-compose up
```

MySQL estará em: `localhost:3306`

## Solução de Problemas

### Porta 5000 já em uso

```bash
# Mudar porta no docker-compose.yml
ports:
  - "8000:5000"  # Acessar em http://localhost:8000

# Ou liberar a porta
# Windows: netstat -ano | findstr :5000
# Linux: sudo lsof -i :5000 | grep python
```

### Container não inicia

```bash
# Ver erro completo
docker-compose logs flask-app

# Rebuild sem cache
docker-compose build --no-cache

# Ver recursos disponíveis
docker stats
```

### Dados desaparecem

Os dados do SQLite estão em `./instance/estoque.db` no seu PC.

**Se usar volumes corretamente, dados persistem.**

### ModuleNotFoundError

```bash
# Reinstalar dependências
docker-compose build --no-cache

# Ou dentro do container
docker-compose exec flask-app pip install -r requirements.txt
```

## Deployment (Produção)

### Opção 1: Docker Hub

```bash
# Build e tag
docker build -t seu-usuario/estoque:latest .

# Push
docker push seu-usuario/estoque:latest

# Em outro PC
docker run -p 5000:5000 seu-usuario/estoque:latest
```

### Opção 2: Docker Compose em Servidor

```bash
# Em um servidor com Docker instalado
git clone seu-repo
docker-compose -f docker-compose.prod.yml up -d
```

### Opção 3: Railway/Render (sem instalar Docker)

1. Push para GitHub
2. Conectar em Railway ou Render
3. Deploy automático

## Performance

### Optimizações

```dockerfile
# Multi-stage build (reduz tamanho)
FROM python:3.11 as builder
# ... instalar dependências

FROM python:3.11-slim
# Copiar apenas o necessário
```

### Ver tamanho da imagem

```bash
docker images
```

## Limpeza

```bash
# Remover imagens não usadas
docker image prune

# Remover containers parados
docker container prune

# Remover volumes não usados
docker volume prune

# Remover tudo (CUIDADO!)
docker system prune -a
```

## Próximos Passos

1. ✅ Instale Docker Desktop/Engine
2. ✅ Execute `docker-compose up`
3. ✅ Acesse `http://localhost:5000`
4. ✅ Edite código e veja mudanças em tempo real
5. ✅ Compartilhe com time - tudo funciona igual

## Referências

- Docker Docs: https://docs.docker.com/
- Docker Compose: https://docs.docker.com/compose/
- Python Docker: https://docs.docker.com/language/python/

---

**Com Docker, você nunca mais vai ouvir "funciona no meu PC"!** 🐳 ✨

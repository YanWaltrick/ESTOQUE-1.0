# Use a imagem oficial do Python 3.11
FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=app.py

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivo de requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copiar código da aplicação
COPY . .

# Copiar script de inicialização
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Criar diretório para o banco de dados
RUN mkdir -p /app/instance

# Expor porta
EXPOSE 5000

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

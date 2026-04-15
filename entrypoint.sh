#!/bin/bash
# entrypoint.sh - Script de inicialização para o container Docker

set -e

echo "============================================================"
echo "Sistema de Estoque - Inicializando no Docker"
echo "============================================================"

# Aguardar banco de dados (se estiver usando MySQL)
if [ ! -z "$DATABASE_URL" ] && [[ "$DATABASE_URL" == mysql* ]]; then
    echo "Aguardando MySQL estar pronto..."
    while ! mysql -h mysql -u root -psenha123 -e "SELECT 1" > /dev/null 2>&1; do
        echo "MySQL ainda não está pronto. Aguardando..."
        sleep 2
    done
    echo "[OK] MySQL está pronto!"
fi

# Inicializar banco de dados
echo "Inicializando banco de dados..."
python init_db_simple.py

echo "Iniciando aplicação Flask..."
exec python app.py

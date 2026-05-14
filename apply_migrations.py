#!/usr/bin/env python
"""
Script para aplicar migrações manualmente
"""
import os
import sys
from app import create_app, db
from flask_migrate import upgrade, Migrate

# Mudar para o diretório da aplicação
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Criar aplicação
app = create_app()

# Inicializar Flask-Migrate
migrate = Migrate(app, db, directory='migrations', render_as_batch=True)

# Aplicar migrações
with app.app_context():
    print("Aplicando migrações...")
    try:
        upgrade()
        print("✓ Migrações aplicadas com sucesso!")
    except Exception as e:
        print(f"✗ Erro ao aplicar migrações: {e}")
        sys.exit(1)

#!/usr/bin/env python
"""
Flask CLI para gerenciar a aplicacao
Uso: python manage.py db <comando>
"""

from app import create_app, db
from flask_migrate import Migrate

app = create_app()
migrate = Migrate(app, db, directory='migrations', render_as_batch=True)

@app.cli.command()
def db_init():
    """Inicializa repositorio de migracoes"""
    from flask_migrate import init
    init('migrations')
    print("[OK] Repositorio de migracoes inicializado")

@app.cli.command()
def db_migrate():
    """Gera nova migracao"""
    from flask_migrate import migrate
    migrate(message='Auto migration')
    print("[OK] Migracao gerada")

@app.cli.command()
def db_upgrade():
    """Aplica as migracoes"""
    from flask_migrate import upgrade
    upgrade()
    print("[OK] Migracoes aplicadas")

@app.cli.command()
def db_downgrade():
    """Reverte ultima migracao"""
    from flask_migrate import downgrade
    downgrade()
    print("[OK] Migracao revertida")

if __name__ == '__main__':
    app.cli()

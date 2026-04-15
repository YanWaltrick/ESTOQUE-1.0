"""
Script para inicializar e gerenciar migrações do banco de dados com Flask-Migrate
"""

from app import create_app, db
from flask_migrate import Migrate, init, migrate, upgrade, downgrade
import os

# Criar a aplicação
app = create_app()

# Inicializar Migrate
migrate_obj = Migrate(app, db, directory='migrations')

def init_migrations():
    """Inicializa o repositório de migrações"""
    migrations_dir = os.path.join(app.root_path, '..', 'migrations')
    
    with app.app_context():
        print("Inicializando repositório de migrações...")
        init('migrations')
        print("✓ Repositório de migrações criado com sucesso!")

def create_initial_migration():
    """Cria a primeira migração baseada nos modelos"""
    with app.app_context():
        print("Criando migração inicial...")
        migrate(message='Initial migration with all tables')
        print("✓ Migração inicial criada com sucesso!")

def apply_migrations():
    """Aplica todas as migrações ao banco de dados"""
    with app.app_context():
        print("Aplicando migrações...")
        upgrade()
        print("✓ Migrações aplicadas com sucesso!")

def revert_migration():
    """Reverte a última migração"""
    with app.app_context():
        print("Revertendo última migração...")
        downgrade()
        print("✓ Migração revertida com sucesso!")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) == 1:
        # Se nenhum argumento, faz inicialização completa
        print("Inicializando Flask-Migrate e criando banco de dados...\n")
        try:
            init_migrations()
            print()
            create_initial_migration()
            print()
            apply_migrations()
        except Exception as e:
            print(f"Erro durante a inicialização: {e}")
            import traceback
            traceback.print_exc()
    
    elif sys.argv[1] == 'init':
        init_migrations()
    
    elif sys.argv[1] == 'migrate':
        msg = sys.argv[2] if len(sys.argv) > 2 else 'Auto migration'
        with app.app_context():
            print(f"Criando migração: {msg}")
            migrate(message=msg)
            print("✓ Migração criada!")
    
    elif sys.argv[1] == 'upgrade':
        apply_migrations()
    
    elif sys.argv[1] == 'downgrade':
        revert_migration()
    
    else:
        print(f"Comando desconhecido: {sys.argv[1]}")
        print("Comandos disponíveis:")
        print("  python init_db.py              - Inicializar e configurar tudo")
        print("  python init_db.py init         - Inicializar migrações")
        print("  python init_db.py migrate MSG  - Criar nova migração")
        print("  python init_db.py upgrade      - Aplicar migrações")
        print("  python init_db.py downgrade    - Reverter última migração")

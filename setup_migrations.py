#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script simples para inicializar Flask-Migrate
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

def main():
    """Funcao principal"""
    print("=" * 60)
    print("Inicializando Flask-Migrate para o Sistema de Estoque")
    print("=" * 60 + "\n")
    
    try:
        from app import create_app, db
        from flask_migrate import Migrate, init, migrate, upgrade
        
        # Passo 1: Criar app
        print("Criando aplicacao...")
        app = create_app()
        
        # Passo 2: Inicializar Migrate
        print("[OK] Aplicacao criada\n")
        
        migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        
        # Passo 3: Gerar primeira migracao
        print("Gerando primeira migracao...")
        with app.app_context():
            with app.app.app_context():
                Migrate(app, db, compare_type=True, render_as_batch=True)
                if not os.path.exists(os.path.join(migrations_dir, 'versions')):
                    init('migrations')
                migrate(message='Initial migration')
        
        # Passo 4: Aplicar migracoes
        print("[OK] Primeira migracao gerada\n")
        print("Aplicando migracoes...")
        with app.app_context():
            upgrade()
        
        print("[OK] Migracoes aplicadas com sucesso!\n")
        print("=" * 60)
        print("[OK] Setup completado com sucesso!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print("\n[ERRO] Erro: {}".format(e))
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

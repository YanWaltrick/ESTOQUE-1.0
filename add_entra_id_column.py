#!/usr/bin/env python
"""
Script para adicionar coluna entra_id à tabela users
Run: python add_entra_id_column.py
"""

import sys

from app import create_app, db


def add_entra_id_column():
    """Adiciona coluna entra_id à tabela users se não existir"""
    app = create_app()

    with app.app_context():
        try:
            # Tentar inserir um registro dummy para verificar se coluna existe
            print("Verificando se coluna 'entra_id' já existe...")

            # Usar conexão raw do SQLAlchemy para adicionar coluna
            from sqlalchemy import text

            # Verificar se coluna existe
            with db.engine.connect() as connection:
                try:
                    # Tentar ler a coluna
                    result = connection.execute(text("SELECT entra_id FROM users LIMIT 1"))
                    print("✓ Coluna 'entra_id' já existe na tabela users")
                    return True
                except Exception:
                    print("✗ Coluna 'entra_id' não encontrada, adicionando...")

                    # Adicionar coluna
                    try:
                        connection.execute(
                            text("""
                            ALTER TABLE users 
                            ADD COLUMN entra_id VARCHAR(255) UNIQUE NULL
                        """)
                        )
                        connection.commit()
                        print("✓ Coluna 'entra_id' adicionada com sucesso!")
                        return True
                    except Exception as add_error:
                        print(f"✗ Erro ao adicionar coluna: {str(add_error)}")
                        connection.rollback()
                        return False

        except Exception as e:
            print(f"Erro: {str(e)}")
            return False


if __name__ == "__main__":
    success = add_entra_id_column()
    sys.exit(0 if success else 1)

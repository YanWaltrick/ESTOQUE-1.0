#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para inicializar o banco de dados com segurança melhorada.
Cria tabelas e usuário admin com senha segura.
"""

import os
import sys

def main():
    print("=" * 60)
    print("Inicializando banco de dados com RBAC")
    print("=" * 60)
    
    # Adicionar o diretório raiz ao path
    app_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, app_dir)
    
    try:
        from app import create_app, db
        
        print("\n[1] Criando aplicação...")
        app = create_app()
        
        with app.app_context():
            print("[2] Criando tabelas...")
            db.create_all()
            
            from app.models import User
            from app.auth.security import PasswordValidator
            
            print("[3] Verificando usuário admin...")
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                # Usar PasswordValidator para hash seguro
                password_hash = PasswordValidator.hash_password('Admin@123')
                admin = User(
                    username='admin',
                    password=password_hash,
                    role='admin',
                    area='TI',
                    localizacao='Administrativo'
                )
                db.session.add(admin)
                db.session.commit()
                print("[OK] Usuário admin criado com segurança melhorada!")
            else:
                print("[OK] Usuário admin já existe!")
            
            # Criar usuários de exemplo para teste
            print("[4] Criando usuários de teste...")
            
            # Gerente
            gerente = User.query.filter_by(username='gerente').first()
            if not gerente:
                gerente = User(
                    username='gerente',
                    password=PasswordValidator.hash_password('Gerente@123'),
                    role='gerente',
                    area='Estoque',
                    localizacao='Sala 1'
                )
                db.session.add(gerente)
                print("  - Usuário 'gerente' criado")
            
            # Operador
            operador = User.query.filter_by(username='operador').first()
            if not operador:
                operador = User(
                    username='operador',
                    password=PasswordValidator.hash_password('Operador@123'),
                    role='operador',
                    area='Estoque',
                    localizacao='Sala 2'
                )
                db.session.add(operador)
                print("  - Usuário 'operador' criado")
            
            # Usuário comum
            usuario_comum = User.query.filter_by(username='usuario').first()
            if not usuario_comum:
                usuario_comum = User(
                    username='usuario',
                    password=PasswordValidator.hash_password('Usuario@123'),
                    role='usuario',
                    area='Vendas',
                    localizacao='Sala 3'
                )
                db.session.add(usuario_comum)
                print("  - Usuário 'usuario' criado")
            
            db.session.commit()
        
        print("\n" + "=" * 60)
        print("[OK] Banco de dados inicializado com sucesso!")
        print("=" * 60)
        print("\nCredenciais de teste:")
        print("-" * 60)
        print("Admin:")
        print("  Usuário: admin")
        print("  Senha: Admin@123")
        print("  Permissões: Tudo")
        print()
        print("Gerente:")
        print("  Usuário: gerente")
        print("  Senha: Gerente@123")
        print("  Permissões: Criar/editar produtos, criar usuários")
        print()
        print("Operador:")
        print("  Usuário: operador")
        print("  Senha: Operador@123")
        print("  Permissões: Registrar entrada/saída, visualizar estoque")
        print()
        print("Usuário:")
        print("  Usuário: usuario")
        print("  Senha: Usuario@123")
        print("  Permissões: Visualizar estoque, criar chamados")
        print("-" * 60)
        print("\nAcesse: http://127.0.0.1:5000/login")
        print("=" * 60)
        
        return 0
        print("  Usuario: admin")
        print("  Senha:   admin")
        print("\nProximos passos:")
        print("  1. Iniciar servidor: python app.py")
        print("  2. Acessar http://127.0.0.1:5000")
        
        return 0
        
    except Exception as e:
        print("\n[ERRO] Falha ao inicializar: {}".format(e))
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

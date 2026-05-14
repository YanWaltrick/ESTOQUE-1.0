#!/usr/bin/env python
"""
Script para criar todas as tabelas no MySQL
Executa: python create_tables.py
"""

import os
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def create_tables():
    """Cria todas as tabelas no banco de dados"""
    
    # Verificar se DATABASE_URL está configurada
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("\n❌ ERRO: DATABASE_URL não está configurada em .env")
        print("   Configure como:")
        print("   DATABASE_URL=mysql+pymysql://user:password@localhost:3306/estoque")
        sys.exit(1)
    
    if 'mysql' not in database_url:
        print("\n❌ ERRO: DATABASE_URL não é MySQL")
        print(f"   Encontrada: {database_url[:50]}...")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("📊 CRIANDO TABELAS NO MYSQL")
    print("="*60)
    
    try:
        # Importar a aplicação e banco de dados
        from app.database import create_app, db
        from app.models import User, Chamada, Produto, Movimentacao, Historico, DocumentoUsuario, ItemRecebido
        
        # Criar aplicação Flask
        print("\n1️⃣  Inicializando aplicação Flask...")
        app, db_instance, mail = create_app()
        
        # Contexto da aplicação
        with app.app_context():
            print("   ✅ Aplicação inicializada")
            
            print("\n2️⃣  Criando tabelas...")
            try:
                db.create_all()
                print("   ✅ Tabelas criadas com sucesso!")
            except Exception as e:
                print(f"   ❌ Erro ao criar tabelas: {e}")
                raise
            
            print("\n3️⃣  Verificando tabelas criadas...")
            
            # Verificar tabelas
            inspector = __import__('sqlalchemy', fromlist=['inspect']).inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\n   Total de tabelas: {len(tables)}")
            for table in sorted(tables):
                print(f"      ✅ {table}")
            
            # Verificar se admin existe
            print("\n4️⃣  Verificando usuário admin...")
            admin = User.query.filter_by(role='admin').first()
            
            if not admin:
                print("   ⚠️  Nenhum admin encontrado. Criando admin padrão...")
                from app.auth.security import PasswordValidator
                
                admin_user = User(
                    username='admin',
                    password=PasswordValidator.hash_password('admin123'),
                    role='admin',
                    area='Administração',
                    empresa='Sistema',
                    departamento='TI'
                )
                db.session.add(admin_user)
                db.session.commit()
                print("   ✅ Admin criado: username='admin', password='admin123'")
                print("   ⚠️  MUDE A SENHA IMEDIATAMENTE APÓS O LOGIN!")
            else:
                print(f"   ✅ Admin encontrado: {admin.username}")
            
            print("\n" + "="*60)
            print("✅ TUDO PRONTO!")
            print("="*60)
            print("\nPróximos passos:")
            print("1. Acesse: http://localhost:5000")
            print("2. Login: admin / admin123")
            print("3. Altere a senha do admin no perfil")
            print("4. Crie novos usuários com os novos campos")
            
            return True
    
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        success = create_tables()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

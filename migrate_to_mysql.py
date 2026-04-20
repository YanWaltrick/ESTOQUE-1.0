#!/usr/bin/env python
"""
Script de migração de dados de SQLite para MySQL
Preserva todos os dados, relacionamentos e sequências de ID

Uso:
    python migrate_to_mysql.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def migrate_data():
    """Migra dados de SQLite para MySQL"""
    
    # Verificar se DATABASE_URL está configurada para MySQL
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url or 'mysql' not in database_url:
        print("\n❌ ERRO: DATABASE_URL não está configurada para MySQL")
        print("   Configure no arquivo .env:")
        print("   DATABASE_URL=mysql+pymysql://user:password@localhost:3306/estoque")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("🔄 MIGRANDO DADOS: SQLite → MySQL")
    print("="*60)
    
    try:
        from app.database import create_app, db
        from app.models import User, Chamada, Produto, Movimentacao, Historico
        
        # Criar aplicação com configuração do .env
        app, db_instance, mail = create_app()
        
        with app.app_context():
            print("\n1️⃣  Criando tabelas no MySQL...")
            db.create_all()
            print("   ✅ Tabelas criadas com sucesso")
            
            print("\n2️⃣  Lendo dados do SQLite (estoque.db)...")
            
            # Conectar ao SQLite
            import sqlite3
            sqlite_conn = sqlite3.connect('estoque.db')
            sqlite_conn.row_factory = sqlite3.Row
            cursor = sqlite_conn.cursor()
            
            # Extrair usuários
            print("   📋 Lendo usuários...")
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            print(f"      Encontrados: {len(users)} usuários")
            
            # Extrair chamadas
            print("   📋 Lendo chamadas...")
            cursor.execute("SELECT * FROM chamada")
            chamadas = cursor.fetchall()
            print(f"      Encontradas: {len(chamadas)} chamadas")
            
            # Extrair produtos
            print("   📋 Lendo produtos...")
            cursor.execute("SELECT * FROM produto")
            produtos = cursor.fetchall()
            print(f"      Encontrados: {len(produtos)} produtos")
            
            # Extrair movimentações
            print("   📋 Lendo movimentações...")
            cursor.execute("SELECT * FROM movimentacao")
            movimentacoes = cursor.fetchall()
            print(f"      Encontradas: {len(movimentacoes)} movimentações")
            
            # Extrair históricos
            print("   📋 Lendo históricos...")
            cursor.execute("SELECT * FROM historico")
            historicos = cursor.fetchall()
            print(f"      Encontrados: {len(historicos)} históricos")
            
            sqlite_conn.close()
            
            print("\n3️⃣  Inserindo dados no MySQL...")
            
            # Inserir usuários
            print("   👤 Inserindo usuários...")
            for user in users:
                try:
                    new_user = User(
                        id=user['id'],
                        username=user['username'],
                        email=user['email'],
                        password_hash=user['password_hash'],
                        is_admin=user['is_admin'],
                        foto_anexo=user['foto_anexo']
                    )
                    db.session.merge(new_user)
                except Exception as e:
                    print(f"      ⚠️  Erro ao inserir usuário {user['username']}: {e}")
            
            db.session.commit()
            print(f"      ✅ {len(users)} usuários inseridos")
            
            # Inserir produtos
            print("   📦 Inserindo produtos...")
            for produto in produtos:
                try:
                    new_product = Produto(
                        id=produto['id'],
                        nome=produto['nome'],
                        descricao=produto['descricao'],
                        quantidade=produto['quantidade'],
                        preco_unitario=produto['preco_unitario'],
                        categoria=produto['categoria'],
                        data_criacao=produto['data_criacao']
                    )
                    db.session.merge(new_product)
                except Exception as e:
                    print(f"      ⚠️  Erro ao inserir produto {produto['nome']}: {e}")
            
            db.session.commit()
            print(f"      ✅ {len(produtos)} produtos inseridos")
            
            # Inserir chamadas
            print("   🎫 Inserindo chamadas...")
            for chamada in chamadas:
                try:
                    new_chamada = Chamada(
                        id=chamada['id'],
                        usuario_id=chamada['usuario_id'],
                        titulo=chamada['titulo'],
                        descricao=chamada['descricao'],
                        area=chamada['area'],
                        cidade=chamada['cidade'],
                        status=chamada['status'],
                        prioridade=chamada['prioridade'],
                        data_criacao=chamada['data_criacao'],
                        data_atualizacao=chamada['data_atualizacao'],
                        foto_anexo=chamada['foto_anexo']
                    )
                    db.session.merge(new_chamada)
                except Exception as e:
                    print(f"      ⚠️  Erro ao inserir chamada ID {chamada['id']}: {e}")
            
            db.session.commit()
            print(f"      ✅ {len(chamadas)} chamadas inseridas")
            
            # Inserir movimentações
            print("   ↔️  Inserindo movimentações...")
            for movimentacao in movimentacoes:
                try:
                    new_movimentacao = Movimentacao(
                        id=movimentacao['id'],
                        produto_id=movimentacao['produto_id'],
                        tipo=movimentacao['tipo'],
                        quantidade=movimentacao['quantidade'],
                        motivo=movimentacao['motivo'],
                        usuario_id=movimentacao['usuario_id'],
                        data_movimentacao=movimentacao['data_movimentacao']
                    )
                    db.session.merge(new_movimentacao)
                except Exception as e:
                    print(f"      ⚠️  Erro ao inserir movimentação ID {movimentacao['id']}: {e}")
            
            db.session.commit()
            print(f"      ✅ {len(movimentacoes)} movimentações inseridas")
            
            # Inserir históricos
            print("   📚 Inserindo históricos...")
            for historico in historicos:
                try:
                    new_historico = Historico(
                        id=historico['id'],
                        usuario_id=historico['usuario_id'],
                        acao=historico['acao'],
                        descricao=historico['descricao'],
                        tabela_afetada=historico['tabela_afetada'],
                        id_registro=historico['id_registro'],
                        data_acao=historico['data_acao']
                    )
                    db.session.merge(new_historico)
                except Exception as e:
                    print(f"      ⚠️  Erro ao inserir histórico ID {historico['id']}: {e}")
            
            db.session.commit()
            print(f"      ✅ {len(historicos)} históricos inseridos")
            
            print("\n4️⃣  Validando migração...")
            
            # Validar contagens
            user_count = User.query.count()
            chamada_count = Chamada.query.count()
            produto_count = Produto.query.count()
            movimentacao_count = Movimentacao.query.count()
            historico_count = Historico.query.count()
            
            print(f"   Usuários: {user_count}")
            print(f"   Chamadas: {chamada_count}")
            print(f"   Produtos: {produto_count}")
            print(f"   Movimentações: {movimentacao_count}")
            print(f"   Históricos: {historico_count}")
            
            # Verificar se as contagens coincidem
            if (user_count == len(users) and 
                chamada_count == len(chamadas) and
                produto_count == len(produtos) and
                movimentacao_count == len(movimentacoes) and
                historico_count == len(historicos)):
                
                print("\n" + "="*60)
                print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
                print("="*60)
                print("\n📌 Próximos passos:")
                print("   1. Faça um backup do arquivo estoque.db (opcional)")
                print("   2. Execute: python app.py")
                print("   3. A aplicação agora usará MySQL")
                print("\n💡 Dica: Você pode manter estoque.db como backup")
                print("="*60 + "\n")
                
                return True
            else:
                print("\n❌ ERRO: Contagens não coincidem!")
                print("   Verifique se houve erros na inserção acima")
                return False
        
    except ImportError as e:
        print(f"\n❌ ERRO: Falta importar módulos - {e}")
        print("   Execute: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO NA MIGRAÇÃO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    success = migrate_data()
    sys.exit(0 if success else 1)

#!/usr/bin/env python
"""
Script de verificação de pré-requisitos para MySQL
Verifica se tudo está pronto para usar a aplicação

Uso:
    python check_mysql_setup.py
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    print("\n" + "="*60)
    print(f"🔍 {text}")
    print("="*60)

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

def print_warning(text):
    print(f"⚠️  {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def check_all():
    """Verifica todos os pré-requisitos"""
    
    print_header("VERIFICAÇÃO DE PRÉ-REQUISITOS - MySQL")
    
    checks_passed = 0
    checks_total = 0
    
    # 1. Verificar MySQL instalado
    print_header("1. MySQL Instalado")
    checks_total += 1
    
    try:
        result = subprocess.run(
            ['mysql', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print_success(f"MySQL encontrado: {version}")
            checks_passed += 1
        else:
            print_error("MySQL não encontrado no PATH")
    except Exception as e:
        print_error(f"Erro ao verificar MySQL: {e}")
    
    # 2. Verificar .env existe
    print_header("2. Arquivo .env")
    checks_total += 1
    
    if os.path.exists('.env'):
        print_success("Arquivo .env encontrado")
        checks_passed += 1
        
        # Verificar DATABASE_URL
        try:
            from dotenv import load_dotenv
            load_dotenv()
            db_url = os.getenv('DATABASE_URL')
            
            if db_url:
                if 'mysql' in db_url:
                    print_success(f"DATABASE_URL configurada para MySQL")
                    # Extrair dados da URL
                    if 'pymysql' in db_url:
                        print_info("Driver: PyMySQL")
                else:
                    print_warning(f"DATABASE_URL não está em MySQL: {db_url[:50]}...")
            else:
                print_warning("DATABASE_URL não configurada em .env")
        except Exception as e:
            print_warning(f"Erro ao ler .env: {e}")
    else:
        print_error("Arquivo .env não encontrado")
        print_info("Execute: python setup_mysql.py")
    
    # 3. Verificar requirements.txt
    print_header("3. Dependências (requirements.txt)")
    checks_total += 1
    
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
            if 'pymysql' in content:
                print_success("PyMySQL encontrado em requirements.txt")
                checks_passed += 1
            else:
                print_error("PyMySQL não encontrado em requirements.txt")
    except Exception as e:
        print_error(f"Erro ao ler requirements.txt: {e}")
    
    # 4. Verificar pacotes instalados
    print_header("4. Pacotes Python Instalados")
    checks_total += 1
    
    try:
        import pymysql
        print_success("pymysql instalado")
        checks_passed += 1
    except ImportError:
        print_error("pymysql NÃO está instalado")
        print_info("Execute: pip install pymysql")
    
    # 5. Verificar Flask-SQLAlchemy
    print_header("5. Flask-SQLAlchemy")
    checks_total += 1
    
    try:
        import flask_sqlalchemy
        print_success("flask-sqlalchemy instalado")
        checks_passed += 1
    except ImportError:
        print_error("flask-sqlalchemy NÃO está instalado")
    
    # 6. Verificar arquivos de migração
    print_header("6. Scripts de Migração")
    checks_total += 1
    
    required_files = [
        'migrate_to_mysql.py',
        'setup_mysql.py',
        'MYSQL_SETUP.md',
        'QUICK_START_MYSQL.md'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print_success(f"{file}")
        else:
            print_error(f"{file} NÃO encontrado")
            all_exist = False
    
    if all_exist:
        checks_passed += 1
    
    # 7. Verificar estoque.db (SQLite anterior)
    print_header("7. Banco de Dados SQLite (para migração)")
    checks_total += 1
    
    if os.path.exists('estoque.db'):
        size_mb = os.path.getsize('estoque.db') / (1024 * 1024)
        print_success(f"estoque.db encontrado ({size_mb:.2f} MB)")
        print_info("Este arquivo será lido durante a migração")
        checks_passed += 1
    else:
        print_warning("estoque.db não encontrado (pode estar em outro lugar)")
    
    # 8. Verificar diretórios de upload
    print_header("8. Diretórios de Upload")
    checks_total += 1
    
    upload_dirs = [
        'static/uploads/chamadas',
        'static/uploads/avatars'
    ]
    
    all_exist = True
    for dir_path in upload_dirs:
        if os.path.exists(dir_path):
            print_success(f"{dir_path}")
        else:
            print_info(f"{dir_path} será criado quando necessário")
            all_exist = False
    
    if all_exist:
        checks_passed += 1
    else:
        checks_passed += 1  # Contar como ok pois serão criados automaticamente
    
    # 9. Tentar conectar ao MySQL
    print_header("9. Conexão com MySQL")
    checks_total += 1
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        import pymysql
        
        db_url = os.getenv('DATABASE_URL')
        if db_url and 'mysql' in db_url:
            # Extrair credenciais da URL
            # Formato: mysql+pymysql://user:pass@host:port/database
            try:
                parts = db_url.replace('mysql+pymysql://', '').split('@')
                if len(parts) == 2:
                    creds = parts[0].split(':')
                    host_db = parts[1].split('/')
                    
                    user = creds[0]
                    password = creds[1] if len(creds) > 1 else ''
                    host = host_db[0].split(':')[0]
                    port = int(host_db[0].split(':')[1]) if ':' in host_db[0] else 3306
                    database = host_db[1]
                    
                    conn = pymysql.connect(
                        host=host,
                        user=user,
                        password=password,
                        database=database,
                        port=port
                    )
                    print_success(f"Conectado com sucesso a {database}@{host}:{port}")
                    
                    # Verificar tabelas
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", (database,))
                    table_count = cursor.fetchone()[0]
                    print_info(f"Banco tem {table_count} tabelas")
                    
                    conn.close()
                    checks_passed += 1
            except Exception as e:
                print_warning(f"Erro ao extrair credenciais da URL: {e}")
        else:
            print_warning("DATABASE_URL não configurada para MySQL")
    except ImportError:
        print_warning("pymysql não está instalado - teste de conexão ignorado")
    except Exception as e:
        print_warning(f"MySQL não está rodando ou conexão falhou: {e}")
        print_info("Para iniciar MySQL: net start MySQL80 (Windows)")
    
    # Resumo
    print_header("RESUMO")
    
    percentage = (checks_passed / checks_total) * 100
    print(f"\nVerificações passadas: {checks_passed}/{checks_total} ({percentage:.0f}%)\n")
    
    if percentage == 100:
        print_success("TUDO PRONTO! Você pode executar: python migrate_to_mysql.py")
        return True
    elif percentage >= 70:
        print_warning("PARCIALMENTE PRONTO - Corrija os itens com ❌")
        return False
    else:
        print_error("NÃO ESTÁ PRONTO - Execute: python setup_mysql.py")
        return False

if __name__ == '__main__':
    try:
        success = check_all()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Verificação cancelada")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

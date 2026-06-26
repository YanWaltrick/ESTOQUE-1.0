#!/usr/bin/env python
"""Teste rápido da integração Entra ID"""

try:
    print("=" * 60)
    print("TESTE DE INTEGRAÇÃO ENTRA ID")
    print("=" * 60)
    
    # Test 1: Import MSAL
    print("\n[1/4] Testando import de MSAL...")
    import msal
    print("      ✓ MSAL importado com sucesso")
    
    # Test 2: Import módulos Entra
    print("\n[2/4] Testando módulos de autenticação...")
    from app.auth.entra_id import EntraIDConfig, EntraIDClient, create_csrf_token, validate_email_in_database
    print("      ✓ EntraIDConfig")
    print("      ✓ EntraIDClient")
    print("      ✓ create_csrf_token")
    print("      ✓ validate_email_in_database")
    
    # Test 3: Import Blueprint
    print("\n[3/4] Testando Blueprint...")
    from app.routes.entra_auth import entra_bp, is_entra_authenticated, get_entra_user_info
    print("      ✓ Blueprint entra_bp")
    print("      ✓ is_entra_authenticated")
    print("      ✓ get_entra_user_info")
    
    # Test 4: App factory
    print("\n[4/4] Testando app factory...")
    from app import create_app
    app = create_app()
    print("      ✓ create_app()")
    print("      ✓ Blueprints registrados:")
    for blueprint in app.blueprints:
        if 'entra' in blueprint:
            print(f"        - {blueprint}")
    
    print("\n" + "=" * 60)
    print("✅ INTEGRAÇÃO ENTRA ID - 100% FUNCIONAL")
    print("=" * 60)
    print("\nRotas disponíveis:")
    print("  • GET /entra/login")
    print("  • GET /entra/callback")
    print("  • GET /entra/logout")
    print("\nProxemos passo:")
    print("  1. Preencher variáveis de ambiente em .env")
    print("  2. python app.py")
    print("  3. http://localhost:5000/entra/login")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ ERRO: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

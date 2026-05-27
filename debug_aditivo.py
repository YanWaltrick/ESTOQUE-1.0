#!/usr/bin/env python
"""Script para debugar a criação do aditivo"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import User, TermoEntrega, DocumentoUsuario

app = create_app()

with app.app_context():
    # Encontrar o usuário teste6
    teste6 = User.query.filter_by(username='teste6').first()
    
    if not teste6:
        print("❌ Usuário teste6 não encontrado")
        sys.exit(1)
    
    print(f"✅ Usuário teste6 encontrado (ID: {teste6.id})")
    
    # Verificar documentos do teste6
    documentos = DocumentoUsuario.query.filter_by(id_usuario=teste6.id).all()
    
    print(f"\n📄 Documentos do usuário teste6 ({len(documentos)} total):")
    for doc in documentos:
        print(f"  - ID: {doc.id_documento}")
        print(f"    Nome: {doc.nome_documento}")
        print(f"    Arquivo: {doc.arquivo}")
        print(f"    Tamanho: {doc.tamanho_arquivo}")
        print(f"    Enviado por: {getattr(doc, 'usuario_enviador', 'N/A')}")
        print(f"    ---")
    
    # Verificar termo de entrega
    termo = TermoEntrega.query.filter_by(id_usuario=teste6.id).first()
    if termo:
        print(f"\n✅ Termo de Entrega encontrado")
        eq_preview = termo.equipamentos[:100] if termo.equipamentos else 'Nenhum'
        print(f"  Equipamentos preview: {eq_preview}")
    else:
        print(f"\n❌ Termo de Entrega não encontrado")

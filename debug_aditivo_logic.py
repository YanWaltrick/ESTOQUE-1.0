#!/usr/bin/env python
"""Script para debugar a detecção de aditivo"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import User, TermoEntrega, DocumentoUsuario
import json

app = create_app()

with app.app_context():
    # Encontrar o usuário teste6
    teste6 = User.query.filter_by(username='teste6').first()
    user_id = teste6.id
    
    print(f"🔍 Debugando aditivo para teste6 (ID: {user_id})\n")
    
    # Obter equipamentos
    termo = TermoEntrega.query.filter_by(id_usuario=user_id).first()
    
    if not termo:
        print("❌ Termo não encontrado")
        sys.exit(1)
    
    print(f"✅ Termo encontrado")
    
    # Parse equipamentos
    equipamentos = []
    if termo.equipamentos:
        try:
            equipamentos = json.loads(termo.equipamentos) if isinstance(termo.equipamentos, str) else termo.equipamentos
        except Exception as e:
            print(f"❌ Erro ao parsear equipamentos: {e}")
            equipamentos = []
    
    print(f"\n📦 Equipamentos ({len(equipamentos)} total):")
    for i, eq in enumerate(equipamentos):
        print(f"  {i}: {eq.get('descricao', 'N/A')}")
        print(f"     Tem 'tipo_documento'? {'tipo_documento' in eq}")
        if 'tipo_documento' in eq:
            print(f"     tipo_documento = '{eq.get('tipo_documento')}'")
    
    # Verificar documentos existentes
    termo_documento = DocumentoUsuario.query.filter_by(
        id_usuario=user_id,
        nome_documento='Termo de Entrega'
    ).first()
    
    print(f"\n📄 Termo documento existente? {termo_documento is not None}")
    if termo_documento:
        print(f"   ID: {termo_documento.id_documento}")
        print(f"   Nome: {termo_documento.nome_documento}")
        print(f"   Arquivo: {termo_documento.arquivo}")
    
    # Calcular lógica
    tem_tipo_documento = any('tipo_documento' in eq for eq in equipamentos)
    tem_equipamento_aditivo = any(eq.get('tipo_documento') == 'aditivo' for eq in equipamentos)
    
    eh_aditivo = tem_equipamento_aditivo or (termo_documento is not None and not tem_tipo_documento)
    
    print(f"\n🔢 Lógica de detecção:")
    print(f"  tem_tipo_documento = {tem_tipo_documento}")
    print(f"  tem_equipamento_aditivo = {tem_equipamento_aditivo}")
    print(f"  termo_documento is not None = {termo_documento is not None}")
    print(f"  not tem_tipo_documento = {not tem_tipo_documento}")
    print(f"  ")
    print(f"  eh_aditivo = {tem_equipamento_aditivo} OR ({termo_documento is not None} AND {not tem_tipo_documento})")
    print(f"  eh_aditivo = {eh_aditivo}")
    
    print(f"\n{'✅' if eh_aditivo else '❌'} Seria detectado como ADITIVO? {eh_aditivo}")

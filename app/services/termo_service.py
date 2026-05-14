"""
Serviço de geração de PDF para Termo de Entrega e Responsabilidade
Utiliza ReportLab com SimpleDocTemplate e Platypus para documentos editáveis
Mantém formatação legal integral conforme documento original
"""

import json
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.models import User, TermoEntrega


class TermoService:
    """Serviço para gerar Termo de Entrega em PDF com estrutura legal integral"""
    
    @staticmethod
    def gerar_pdf(usuario_id, nome_arquivo=None):
        """
        Gera PDF do Termo de Entrega para um usuário
        
        Args:
            usuario_id: ID do usuário
            nome_arquivo: Nome do arquivo (padrão: arquivo em memória)
            
        Returns:
            BytesIO com conteúdo do PDF ou caminho do arquivo gerado
        """
        # Carregar usuário e termo
        usuario = User.query.get(usuario_id)
        if not usuario:
            raise ValueError(f"Usuário {usuario_id} não encontrado")
        
        termo = TermoEntrega.query.filter_by(id_usuario=usuario_id).first()
        if not termo:
            raise ValueError(f"Termo para usuário {usuario_id} não encontrado")
        
        # Preparar equipamentos
        equipamentos = []
        if termo.equipamentos:
            try:
                equipamentos = json.loads(termo.equipamentos) if isinstance(termo.equipamentos, str) else termo.equipamentos
            except:
                equipamentos = []
        
        # Criar documento (em arquivo ou memória)
        if nome_arquivo:
            doc = SimpleDocTemplate(nome_arquivo, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        else:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        
        styles = getSampleStyleSheet()
        
        # Estilos Personalizados
        style_n = ParagraphStyle('Corpo', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=9, leading=11)
        style_b = ParagraphStyle('Negrito', parent=style_n, fontName='Helvetica-Bold')
        style_t = ParagraphStyle('Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=11, fontName='Helvetica-Bold', spaceAfter=15)
        style_indent = ParagraphStyle('ParagrafoUnico', parent=style_n, leftIndent=20)
        
        elements = []

        # --- TÍTULO ---
        elements.append(Paragraph("TERMO DE ENTREGA E RESPONSABILIDADE PELO USO DE EQUIPAMENTOS DA EMPRESA", style_t))

        # --- PREÂMBULO (Campos de Identificação) ---
        campos = [
            f"Empresa: {termo.empresa or '_________________________________________________'}",
            f"CNPJ: {termo.cnpj or '____________________________________________________'}",
            f"Endereço: {termo.endereco or '_________________________________________________'}",
            f"Colaborador: {termo.nome_colaborador or usuario.username or '_______________________________________________'}",
            f"Cargo/Função (se aplicável): {termo.cargo_funcao or usuario.cargo or '__________________________________'}",
            f"CPF/CNPJ: {termo.cpf_cnpj or usuario.cpf or '________________________________________________'}",
            f"Data de Admissão (se aplicável): {termo.data_admissao.strftime('%d/%m/%Y') if termo.data_admissao else '_______________________________'}",
            f"Departamento (se aplicável): {termo.departamento or usuario.departamento or '___________________________________'}",
            f"Local de trabalho (se aplicável): {termo.local_trabalho or usuario.local_trabalho or '________________________________'}"
        ]
        for campo in campos:
            elements.append(Paragraph(campo, style_n))
            elements.append(Spacer(1, 4))
        
        elements.append(Spacer(1, 10))

        # --- 1. OBJETO ---
        elements.append(Paragraph("1. OBJETO", style_b))
        elements.append(Paragraph("O presente Termo tem por objeto formalizar a entrega, posse e responsabilidade do colaborador quanto ao uso, guarda, conservação e devolução dos equipamentos, dispositivos, acessórios e demais bens de propriedade da empresa, fornecidos para a execução de suas atividades profissionais.", style_n))

        # --- 2. EQUIPAMENTOS ENTREGUES (Tabela) ---
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("2. EQUIPAMENTOS ENTREGUES", style_b))
        elements.append(Paragraph("A empresa declara ter fornecido os seguintes itens ao colaborador, elencado no preâmbulo:", style_n))
        elements.append(Spacer(1, 5))

        data_tab = [["Equipamento / Acessório", "Marca", "Modelo", "Estado", "Data Entrega", "Valor Aproximado"]]
        
        if equipamentos:
            for eq in equipamentos:
                data_tab.append([
                    eq.get('descricao', '')[:30],
                    eq.get('marca', '')[:20],
                    eq.get('modelo', '')[:20],
                    eq.get('estado', '')[:15],
                    eq.get('data_entrega', '')[:12],
                    eq.get('valor', '')[:12]
                ])
        
        # Completar com linhas vazias
        while len(data_tab) < 9:  # Cabeçalho + 8 linhas
            data_tab.append(['', '', '', '', '', ''])
        
        t_equip = Table(data_tab, colWidths=[120, 75, 75, 70, 70, 75])
        t_equip.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
        ]))
        elements.append(t_equip)

        # --- 3. CHECKLIST DE ENTREGA ---
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("3. CHECKLIST DE ENTREGA", style_b))
        elements.append(Paragraph("Considerando o disposto na cláusula anterior, o colaborador declara, nesta data e por meio do checklist abaixo colacionado, ter recebido, na presente data, os seguintes itens de propriedade da empresa, para uso exclusivamente profissional:", style_n))
        
        checklist = [
            "☐ Notebook", "☐ Fonte do notebook", "☐ Mouse", "☐ Mouse Pad", "☐ Teclado",
            "☐ Suporte", "☐ Fone (Headset)", "☐ Condição do Notebook", "☐ Celular",
            "☐ Cabo e carregador", "☐ Demais acessórios/Outros (especificar)", "☐ Funcionamento validado?"
        ]
        for item in checklist:
            elements.append(Paragraph(f"{item} ____________________________________", style_n))

        # --- 4. RESPONSABILIDADES DO COLABORADOR/TERCEIRO ---
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("4. RESPONSABILIDADES DO COLABORADOR/TERCEIRO", style_b))
        textos_4 = [
            "Ao assinar o presente Termo, o colaborador declara ciência e concordância com as seguintes políticas internas:",
            "Zelar pela integridade física e funcional dos equipamentos e acessórios recebidos, utilizando-os com diligência e cuidado, exclusivamente para o desempenho de suas atividades profissionais, salvo autorização expressa da empresa.",
            "Utilizar os equipamentos de forma adequada e em conformidade com as orientações fornecidas pela empresa, abstendo-se de práticas que possam ocasionar danos, tais como quedas, exposição à umidade, transporte inadequado ou instalações indevidas.",
            "Não compartilhar, ceder, emprestar ou permitir o uso dos equipamentos por terceiros não autorizados, salvo mediante autorização prévia e expressa da empresa.",
            "Não instalar, copiar ou utilizar softwares, programas ou aplicações sem a devida autorização da empresa, especialmente aqueles sem licença ou em desconformidade com a legislação vigente, ficando ciente de que eventuais irregularidades poderão ensejar a adoção de medidas cabíveis.",
            "Observar rigorosamente as políticas internas da empresa relacionadas à segurança da informação, proteção de dados e uso de recursos tecnológicos, mantendo o sigilo sobre quaisquer dados, informações ou acessos obtidos em razão da utilização dos equipamentos.",
            "Não compartilhar credenciais de acesso, senhas ou quaisquer mecanismos de autenticação vinculados aos sistemas corporativos.",
            "Comunicar imediatamente à empresa a ocorrência de qualquer defeito, dano, perda, extravio, furto, roubo ou incidente envolvendo os equipamentos e dados, colaborando com a apuração dos fatos.",
            "Devolver os equipamentos nas condições previstas neste Termo, ao término do vínculo empregatício ou sempre que solicitado pela empresa."
        ]
        for t in textos_4:
            elements.append(Paragraph(t, style_n))
            elements.append(Spacer(1, 3))
        
        elements.append(Paragraph("Parágrafo único. O colaborador somente será responsabilizado por danos causados aos equipamentos quando comprovada a ocorrência de dolo ou culpa (negligência, imprudência ou imperícia), não se incluindo hipóteses de desgaste natural decorrente do uso regular, nem situações de caso fortuito ou força maior, devidamente comprovadas.", style_indent))

        # --- 7. AUTORIZAÇÃO DE DESCONTO ---
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("7. AUTORIZAÇÃO DE DESCONTO", style_b))
        elements.append(Paragraph("O colaborador, nos termos do artigo 462 da Consolidação das Leis do Trabalho, autoriza expressamente a empresa a proceder ao desconto em folha de pagamento de valores correspondentes a prejuízos causados aos equipamentos e/ou acessórios sob sua responsabilidade, desde que comprovadamente decorrentes de dolo ou culpa (negligência, imprudência ou imperícia), tais como: mau uso, extravio, perda, não devolução ou danos evitáveis.", style_n))
        
        # --- 10. FORO ---
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("10. FORO", style_b))
        elements.append(Paragraph("Para dirimir eventuais dúvidas oriundas deste Termo, as partes elegem o foro da comarca do local da prestação de serviços do colaborador, nos termos do artigo 651 da Consolidação das Leis do Trabalho.", style_n))
        elements.append(Paragraph("Parágrafo único. Sem prejuízo do disposto no caput, para as hipóteses que não se enquadrem na competência da Justiça do Trabalho ou ainda quando inexistente conflito com as regras legais de competência, fica eleito o foro da comarca de Campinas/SP, com renúncia a qualquer outro, por mais privilegiado que seja.", style_indent))

        # --- 11. DECLARAÇÃO FINAL E ASSINATURAS ---
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("11. DECLARAÇÃO FINAL", style_b))
        elements.append(Paragraph("O colaborador declara, para todos os fins de direito, que recebeu os equipamentos e/ou acessórios descritos neste Termo em perfeitas condições de uso e funcionamento, após conferência, comprometendo-se a cumprir integralmente todas as obrigações relativas à sua utilização, guarda, conservação e devolução.", style_n))
        
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("Local e Data: _________________________________________________", style_n))
        
        elements.append(Spacer(1, 30))
        data_ass = [
            ["Assinatura do Colaborador/Terceiro", "Assinatura da Empresa"],
            ["________________________________", "________________________________"]
        ]
        t_ass = Table(data_ass, colWidths=[240, 240])
        t_ass.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
        ]))
        elements.append(t_ass)

        # Gerar PDF
        doc.build(elements)
        
        if nome_arquivo:
            return nome_arquivo
        else:
            buffer.seek(0)
            return buffer
    
    @staticmethod
    def gerar_pdf_memoria(usuario_id):
        """
        Gera PDF em memória (BytesIO)
        
        Args:
            usuario_id: ID do usuário
            
        Returns:
            BytesIO com conteúdo do PDF
        """
        return TermoService.gerar_pdf(usuario_id, nome_arquivo=None)

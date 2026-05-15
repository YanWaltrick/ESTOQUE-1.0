import json
from io import BytesIO

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus.flowables import KeepTogether
from reportlab.platypus.tables import Table
from reportlab.lib.units import cm

from app.models import TermoEntrega, User


class TermoService:
    @staticmethod
    def gerar_pdf(usuario_id, nome_arquivo=None):
        usuario = User.query.get(usuario_id)
        if not usuario:
            raise ValueError(f"Usuário {usuario_id} não encontrado")

        termo = TermoEntrega.query.filter_by(id_usuario=usuario_id).first()
        if not termo:
            raise ValueError(f"Termo para usuário {usuario_id} não encontrado")

        def valor_texto(valor, fallback=''):
            texto = valor if valor not in (None, '') else fallback
            return str(texto) if texto not in (None, '') else ''

        def valor_data(data, formato='%d/%m/%Y'):
            return data.strftime(formato) if data else ''

        equipamentos = []
        if termo.equipamentos:
            try:
                equipamentos = json.loads(termo.equipamentos) if isinstance(termo.equipamentos, str) else termo.equipamentos
            except Exception:
                equipamentos = []

        if equipamentos:
            table_data = [["Equipamento / Acessório", "Marca", "Modelo", "Estado", "Data Entrega", "Valor Aproximado"]]
            for equipamento in equipamentos:
                table_data.append([
                    valor_texto(equipamento.get('descricao', '')),
                    valor_texto(equipamento.get('marca', '')),
                    valor_texto(equipamento.get('modelo', '')),
                    valor_texto(equipamento.get('estado', '')),
                    valor_texto(equipamento.get('data_entrega', '')),
                    valor_texto(equipamento.get('valor', '')),
                ])
        else:
            table_data = [
                ["Equipamento / Acessório", "Marca", "Modelo", "Estado", "Data Entrega", "Valor Aproximado"],
                ["", "", "", "", "", ""],
                ["", "", "", "", "", ""],
                ["", "", "", "", "", ""],
                ["", "", "", "", "", ""],
                ["", "", "", "", "", ""],
                ["", "", "", "", "", ""],
                ["", "", "", "", "", ""],
            ]

        buffer = None
        if nome_arquivo:
            doc = SimpleDocTemplate(
                nome_arquivo,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
        else:
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )

        styles = getSampleStyleSheet()

        style_title = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=14,
            leading=18,
            spaceAfter=20
        )

        style_normal = ParagraphStyle(
            'Normal',
            parent=styles['BodyText'],
            alignment=TA_JUSTIFY,
            fontSize=10,
            leading=14,
            spaceAfter=10
        )

        style_section = ParagraphStyle(
            'Section',
            parent=styles['Heading2'],
            fontSize=11,
            leading=14,
            spaceBefore=12,
            spaceAfter=8
        )

        elements = []

        title = "TERMO DE ENTREGA E RESPONSABILIDADE PELO USO DE EQUIPAMENTOS DA EMPRESA"
        elements.append(Paragraph(title, style_title))

        campos = [
            f"Empresa:  {valor_texto(termo.empresa, usuario.empresa)}",
            f"CNPJ:  {valor_texto(termo.cnpj, usuario.cnpj)}",
            f"Endereço:  {valor_texto(termo.endereco, usuario.endereco)}",
            f"Colaborador: {valor_texto(termo.nome_colaborador, usuario.username)}",
            f"Cargo/Função (se aplicável):  {valor_texto(termo.cargo_funcao, usuario.cargo)}",
            f"CPF/CNPJ:  {valor_texto(termo.cpf_cnpj, usuario.cpf)}",
            f"Data de Admissão  (se aplicável): {valor_data(termo.data_admissao or usuario.data_admissao)}",
            f"Departamento (se aplicável): {valor_texto(termo.departamento, usuario.departamento)}",
            f"Local de trabalho (se aplicável): {valor_texto(termo.local_trabalho, usuario.local_trabalho)}"
        ]

        for campo in campos:
            elements.append(Paragraph(campo, style_normal))

        texto = """
<b>1. OBJETO</b><br/>
O presente Termo tem por objeto formalizar a entrega, posse e responsabilidade do colaborador quanto ao uso, guarda, conservação e devolução dos equipamentos, dispositivos, acessórios e demais bens de propriedade da empresa, fornecidos para a execução de suas atividades profissionais.
"""

        elements.append(Paragraph(texto, style_normal))

        elements.append(Paragraph("<b>2. EQUIPAMENTOS ENTREGUES</b>", style_section))

        texto2 = """
A empresa declara ter fornecido os seguintes itens ao colaborador, elencado no preâmbulo:
"""

        elements.append(Paragraph(texto2, style_normal))

        table = Table(table_data, colWidths=[5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm])

        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('TOPPADDING', (0,1), (-1,-1), 10),
            ('BOTTOMPADDING', (0,1), (-1,-1), 10),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        checklist = """
<b>3. CHECKLIST DE ENTREGA</b><br/><br/>

Considerando o disposto na cláusula anterior, o colaborador declara, nesta data e por meio do checklist abaixo colacionado, ter recebido, na presente data, os seguintes itens de propriedade da empresa, para uso exclusivamente profissional:<br/><br/>

☐ Notebook ____________________________________<br/>
☐ Fonte do notebook ____________________________________<br/>
☐ Mouse ____________________________________<br/>
☐ Mouse Pad____________________________________<br/>
☐ Teclado ____________________________________<br/>
☐ Suporte ____________________________________<br/>
☐ Fone (Headset) ____________________________________<br/>
☐ Condição do Notebook ____________________________________<br/>
☐ Celular ____________________________________<br/>
☐ Cabo e carregador ____________________________________<br/>
☐ Demais acessórios/Outros (especificar) ____________________________________<br/>
☐ Funcionamento validado?____________________________________
"""

        elements.append(Paragraph(checklist, style_normal))

        texto_completo = """
<b>4. RESPONSABILIDADES DO COLABORADOR/TERCEIRO</b><br/><br/>

Ao assinar o presente Termo, o colaborador declara ciência e concordância com as seguintes políticas internas:<br/><br/>

I. Zelar pela integridade física e funcional dos equipamentos e acessórios recebidos, utilizando-os com diligência e cuidado, exclusivamente para o desempenho de suas atividades profissionais, salvo autorização expressa da empresa.<br/><br/>

II. Utilizar os equipamentos de forma adequada e em conformidade com as orientações fornecidas pela empresa, abstendo-se de práticas que possam ocasionar danos, tais como quedas, exposição à umidade, transporte inadequado ou instalações indevidas.<br/><br/>

III. Não compartilhar, ceder, emprestar ou permitir o uso dos equipamentos por terceiros não autorizados, salvo mediante autorização prévia e expressa da empresa.<br/><br/>

IV. Não instalar, copiar ou utilizar softwares, programas ou aplicações sem a devida autorização da empresa, especialmente aqueles sem licença ou em desconformidade com a legislação vigente, ficando ciente de que eventuais irregularidades poderão ensejar a adoção de medidas cabíveis.<br/><br/>

V. Observar rigorosamente as políticas internas da empresa relacionadas à segurança da informação, proteção de dados e uso de recursos tecnológicos, mantendo o sigilo sobre quaisquer dados, informações ou acessos obtidos em razão da utilização dos equipamentos.<br/><br/>

VI. Não compartilhar credenciais de acesso, senhas ou quaisquer mecanismos de autenticação vinculados aos sistemas corporativos.<br/><br/>

VII. Comunicar imediatamente à empresa a ocorrência de qualquer defeito, dano, perda, extravio, furto, roubo ou incidente envolvendo os equipamentos e dados, colaborando com a apuração dos fatos.<br/><br/>

VIII. Devolver os equipamentos nas condições previstas neste Termo, ao término do vínculo empregatício ou sempre que solicitado pela empresa.<br/><br/>

Parágrafo único. O colaborador somente será responsabilizado por danos causados aos equipamentos quando comprovada a ocorrência de dolo ou culpa (negligência, imprudência ou imperícia), não se incluindo hipóteses de desgaste natural decorrente do uso regular, nem situações de caso fortuito ou força maior, devidamente comprovadas.<br/><br/>

<b>5. POLÍTICAS DE USO E SEGURANÇA DIGITAL</b><br/><br/>

O colaborador declara estar ciente e concorda em cumprir integralmente as políticas internas da empresa relacionadas ao uso de equipamentos, segurança da informação e proteção de dados, comprometendo-se a observar, em especial, as seguintes diretrizes:<br/><br/>

I. Utilizar os equipamentos corporativos em conformidade com as normas internas da empresa, abstendo-se de qualquer uso indevido, ilícito ou em desacordo com suas atividades profissionais.<br/><br/>

II. Observar as diretrizes relativas à segurança da informação, incluindo, mas não se limitando, à proteção de dados corporativos, confidenciais e pessoais, nos termos da Lei Geral de Proteção de Dados Pessoais.<br/><br/>

III. Não copiar, reproduzir, armazenar, compartilhar ou transferir, por qualquer meio, informações corporativas em dispositivos pessoais ou de terceiros, sem prévia e expressa autorização da empresa.<br/><br/>

IV. Adotar boas práticas de segurança digital, incluindo a utilização adequada de senhas, bloqueio de dispositivos, atualização de sistemas e prevenção contra acessos não autorizados.<br/><br/>

V. Não acessar, armazenar ou compartilhar conteúdos ilícitos, impróprios ou que possam comprometer a segurança dos sistemas e da rede corporativa.<br/><br/>

VI. Permitir, quando solicitado, a realização de auditorias, verificações ou monitoramento nos equipamentos corporativos, para fins de segurança da informação, compliance e proteção de ativos da empresa, observada a legislação aplicável, incluindo a LGPD, e respeitando a intimidade do colaborador/terceiro, bem como os princípios da transparência e proporcionalidade.<br/><br/>

Parágrafo primeiro. O colaborador/terceiro reconhece que os equipamentos fornecidos pela empresa são ferramentas de trabalho/para realização da atividade profissional e não devem ser usados para fins pessoais (armazenamento de fotos, arquivos pessoais, e-mails privados, etc).<br/><br/>

Parágrafo segundo. O descumprimento das disposições previstas neste item poderá ensejar a adoção de medidas disciplinares, sem prejuízo da responsabilização civil e, quando aplicável, administrativa e penal.
"""

        elements.append(Paragraph(texto_completo, style_normal))

        texto_final = """
<b>6. CONDIÇÕES DE DEVOLUÇÃO</b><br/><br/>

No ato da devolução, a empresa realizará a conferência e inspeção dos equipamentos e acessórios entregues ao colaborador, a fim de verificar seu estado de conservação e funcionamento.<br/><br/>

Parágrafo primeiro. Os equipamentos deverão ser devolvidos em condições compatíveis com o uso regular, ressalvados os desgastes naturais decorrentes da utilização normal.<br/><br/>

Parágrafo segundo. Caso seja constatada a existência de danos, ausência de itens, defeitos ou avarias, a empresa procederá à apuração das circunstâncias, a fim de verificar eventual responsabilidade do colaborador, especialmente nos casos de dolo ou culpa (negligência, imprudência ou imperícia).<br/><br/>

Parágrafo terceiro. Constatada a responsabilidade do colaborador, este poderá ser obrigado ao ressarcimento dos prejuízos causados, limitado ao valor necessário ao reparo ou reposição do bem, observado o disposto no artigo 462 da Consolidação das Leis do Trabalho e demais disposições deste Termo.<br/><br/>

Parágrafo quarto. O colaborador deverá comunicar imediatamente à empresa a ocorrência de perda, extravio, furto, roubo ou qualquer incidente envolvendo os equipamentos, apresentando, quando aplicável, o respectivo boletim de ocorrência ou documentação comprobatória.<br/><br/>

Parágrafo quinto. Na hipótese de desligamento, os equipamentos deverão ser devolvidos imediatamente ou em prazo razoável a ser definido pela empresa, mediante solicitação formal.<br/><br/>

Parágrafo sexto. Enquanto não realizada a devolução dos equipamentos ou a regularização de eventuais pendências identificadas, permanecem válidas todas as obrigações previstas neste Termo.<br/><br/>

<b>7. AUTORIZAÇÃO DE DESCONTO</b><br/><br/>

O colaborador, nos termos do artigo 462 da Consolidação das Leis do Trabalho, autoriza expressamente a empresa a proceder ao desconto em folha de pagamento de valores correspondentes a prejuízos causados aos equipamentos e/ou acessórios sob sua responsabilidade, desde que comprovadamente decorrentes de dolo ou culpa (negligência, imprudência ou imperícia), tais como: mau uso, extravio, perda, não devolução ou danos evitáveis.<br/><br/>

Parágrafo primeiro. O desconto será limitado ao valor efetivamente apurado para reparo ou reposição do bem, vedada qualquer cobrança superior ao prejuízo comprovado.<br/><br/>

Parágrafo segundo. A realização de qualquer desconto estará condicionada à prévia apuração dos fatos pela empresa, sendo assegurado ao colaborador o direito de apresentar esclarecimentos e defesa antes da efetivação do desconto.<br/><br/>

Parágrafo terceiro. Fica expressamente ressalvado que não serão passíveis de desconto os danos decorrentes do desgaste natural pelo uso regular do equipamento ou de caso fortuito e força maior, desde que devidamente comprovados.<br/><br/>

Parágrafo quarto. Na hipótese de rescisão contratual, permanecendo pendente a devolução dos equipamentos ou a apuração de eventuais danos, o colaborador autoriza o desconto dos valores correspondentes nas verbas rescisórias, observado o limite legal e sem prejuízo das verbas de natureza alimentar.<br/><br/>

<b>8. VIGÊNCIA</b><br/><br/>

O presente Termo entra em vigor na data de sua assinatura e permanecerá válido por prazo indeterminado, enquanto o colaborador estiver de posse de quaisquer equipamentos, acessórios ou dispositivos fornecidos pela empresa, independentemente de substituição, atualização ou entrega adicional, inclusive aquelas formalizadas por meio de aditivos.<br/><br/>

Parágrafo primeiro. As obrigações de guarda, zelo, uso adequado, sigilo e devolução dos equipamentos subsistirão durante todo o período em que o colaborador permanecer na posse dos bens, inclusive em casos de afastamento, suspensão ou interrupção do contrato de trabalho.<br/><br/>

Parágrafo segundo. Na hipótese de rescisão do contrato de trabalho, as obrigações previstas neste Termo permanecerão válidas até a efetiva devolução de todos os equipamentos.<br/><br/>

<b>9. ASSINATURA ELETRÔNICA</b><br/><br/>

Este documento poderá firmado por meio de assinatura eletrônica avançada ou qualificada, em conformidade com a Lei Federal nº 14.063/2020. Nesse sentido, a assinatura deste documento pressupõe declarada, de forma inequívoca, a concordância do(s) declarante(s), sendo um compromisso vinculante, válido, eficaz e executável, em todos os seus termos, condições e cláusulas, de acordo com o Artigo 10, Parágrafo 2º da Medida Provisória nº 2.200-2/2001 e do Artigo 6º do Decreto 10.278/2020. Por fim, ainda que algum dos signatários venha a assinar digitalmente este documento em local e/ou data diversa da estabelecida, o local e a data de celebração deste documento são, para todos os fins, aqueles abaixo indicados, sendo que este documento produzirá efeitos a partir da data nele indicada.<br/><br/>

<b>10. FORO</b><br/><br/>

Para dirimir eventuais dúvidas oriundas deste Termo, as partes elegem o foro da comarca do local da prestação de serviços do colaborador, nos termos do artigo 651 da Consolidação das Leis do Trabalho.<br/><br/>

Parágrafo único. Sem prejuízo do disposto no caput, para as hipóteses que não se enquadrem na competência da Justiça do Trabalho ou ainda quando inexistente conflito com as regras legais de competência, fica eleito o foro da comarca de Campinas/SP, com renúncia a qualquer outro, por mais privilegiado que seja.<br/><br/>

<b>11. DECLARAÇÃO FINAL</b><br/><br/>

O colaborador declara, para todos os fins de direito, que recebeu os equipamentos e/ou acessórios descritos neste Termo em perfeitas condições de uso e funcionamento, após conferência, comprometendo-se a cumprir integralmente todas as obrigações relativas à sua utilização, guarda, conservação e devolução.<br/><br/>

Declara, ainda, que leu, compreendeu e concorda, por livre e espontânea vontade, com todas as cláusulas e condições estabelecidas neste Termo, bem como com as políticas internas da empresa a ele relacionadas, especialmente aquelas relativas à segurança da informação e à proteção de dados.<br/><br/>

Local e Data: _________________________________________________<br/><br/><br/>

Assinatura do Colaborador/Terceiro<br/><br/><br/>

________________________________<br/><br/><br/>

Assinatura da Empresa<br/><br/><br/>

________________________________

"""

        elements.append(Paragraph(texto_final, style_normal))

        doc.build(elements)

        if nome_arquivo:
            return nome_arquivo

        buffer.seek(0)
        return buffer

    @staticmethod
    def gerar_pdf_memoria(usuario_id):
        return TermoService.gerar_pdf(usuario_id, nome_arquivo=None)

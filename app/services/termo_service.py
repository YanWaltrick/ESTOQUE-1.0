import json
from io import BytesIO

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)

from reportlab.platypus import Image as RLImage

from PIL import Image as PILImage

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from app.models import TermoEntrega, User
from flask import current_app, url_for

import os
import re
import shutil


class TermoService:

    @staticmethod
    def gerar_pdf(usuario_id, nome_arquivo=None, aditivo=False):

        usuario = User.query.get(usuario_id)

        if not usuario:
            raise ValueError(f"Usuario {usuario_id} nao encontrado")

        termo = TermoEntrega.query.filter_by(id_usuario=usuario_id).first()

        if not termo:
            raise ValueError(f"Termo para usuario {usuario_id} nao encontrado")

        def valor_texto(valor, fallback=''):
            texto = valor if valor not in (None, '') else fallback
            return str(texto) if texto not in (None, '') else ''

        def valor_data(data, formato='%d/%m/%Y'):
            return data.strftime(formato) if data else ''

        equipamentos = []

        if termo.equipamentos:
            try:
                equipamentos = (
                    json.loads(termo.equipamentos)
                    if isinstance(termo.equipamentos, str)
                    else termo.equipamentos
                )
            except Exception:
                equipamentos = []

        # ---------------------------------------------------------
        # TABELA DINAMICA DE EQUIPAMENTOS
        # ---------------------------------------------------------

        if equipamentos:

            table_data = [[
                "Equipamento / Acessorio",
                "Marca",
                "Modelo",
                "Estado",
                "Data Entrega",
                "Valor Aproximado"
            ]]

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
                ["Equipamento / Acessorio", "Marca", "Modelo", "Estado", "Data Entrega", "Valor Aproximado"],
                ["", "", "", "", "", ""],
                ["", "", "", "", "", ""],
                ["", "", "", "", "", ""],
                ["", "", "", "", "", ""],
                ["", "", "", "", "", ""],
                ["", "", "", "", "", ""],
            ]

        # ---------------------------------------------------------
        # DOCUMENTO
        # ---------------------------------------------------------

        buffer = None

        if nome_arquivo:

            doc = SimpleDocTemplate(
                nome_arquivo,
                pagesize=A4,
                rightMargin=2 * cm,
                leftMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm
            )

        else:

            buffer = BytesIO()

            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2 * cm,
                leftMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm
            )

        # ---------------------------------------------------------
        # ESTILOS
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # FUNCOES AUXILIARES
        # ---------------------------------------------------------

        def _foto_url_publica(nome_foto: str) -> str:

            try:
                return url_for(
                    'static',
                    filename=f'uploads/termos/{nome_foto}',
                    _external=True
                )

            except Exception:
                return f'/static/uploads/termos/{nome_foto}'

        def _resolver_caminho_foto(nome_foto: str):

            caminhos = [
                os.path.join(
                    current_app.static_folder,
                    'uploads',
                    'termos',
                    nome_foto
                ),

                os.path.join(
                    current_app.root_path,
                    'static',
                    'uploads',
                    'termos',
                    nome_foto
                ),
            ]

            destino = caminhos[0]

            for caminho in caminhos:

                if os.path.exists(caminho):

                    if caminho != destino:

                        os.makedirs(
                            os.path.dirname(destino),
                            exist_ok=True
                        )

                        try:
                            shutil.copy2(caminho, destino)
                        except Exception:
                            pass

                    return destino

            return None

        def _miniatura_foto(nome_foto: str, max_largura: float, max_altura: float):

            img_path = _resolver_caminho_foto(nome_foto)

            if not img_path:
                return None

            with PILImage.open(img_path) as pil_img:
                largura_original, altura_original = pil_img.size

            fator = min(
                max_largura / largura_original,
                max_altura / altura_original,
                1
            )

            largura_final = largura_original * fator
            altura_final = altura_original * fator

            img = RLImage(img_path)

            img.drawWidth = largura_final
            img.drawHeight = altura_final
            img.hAlign = 'CENTER'

            return img

        def _blocos_fotos_em_uma_pagina(lista_equipamentos):

            blocos = []
            equipamentos_validos = [
                equipamento for equipamento in (lista_equipamentos or [])
                if (equipamento.get('fotos') or [])
            ]

            if not equipamentos_validos:
                return blocos

            colunas = 4
            largura_util = A4[0] - (4 * cm)
            largura_coluna = largura_util / colunas
            max_largura_foto = largura_coluna - (0.25 * cm)
            max_altura_foto = 3.4 * cm

            for equipamento in equipamentos_validos:
                nome_item = valor_texto(
                    equipamento.get('descricao', ''),
                    'Item sem descricao'
                )
                service_tag = valor_texto(equipamento.get('service_tag', ''))
                fotos = equipamento.get('fotos') or []

                titulo_item = nome_item
                if service_tag:
                    titulo_item = f'{nome_item} - ServiceTag: {service_tag}'

                blocos.append(Paragraph(titulo_item, style_section))

                blocos.append(Spacer(1, 3))

                celulas = []
                for foto in fotos:
                    if isinstance(foto, dict):
                        arquivo_foto = foto.get('arquivo') or ''
                        titulo_foto = valor_texto(foto.get('titulo'), 'Foto')
                    else:
                        arquivo_foto = foto
                        titulo_foto = 'Foto'

                    miniatura = _miniatura_foto(arquivo_foto, max_largura_foto, max_altura_foto)
                    if miniatura:
                        celulas.append([
                            Paragraph(titulo_foto, style_normal),
                            Spacer(1, 2),
                            miniatura,
                        ])

                if celulas:
                    while len(celulas) % colunas != 0:
                        celulas.append(Spacer(1, 1))

                    linhas = [celulas[i:i + colunas] for i in range(0, len(celulas), colunas)]

                    tabela_fotos = Table(
                        linhas,
                        colWidths=[largura_coluna] * colunas
                    )

                    tabela_fotos.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 1),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
                        ('TOPPADDING', (0, 0), (-1, -1), 1),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                    ]))

                    blocos.append(tabela_fotos)

            return blocos

        # ---------------------------------------------------------
        # ELEMENTOS
        # ---------------------------------------------------------

        elements = []

        # =========================================================
        # TERMO PJ (Pessoa Jurídica)
        # =========================================================
        is_pj = False
        try:
            is_pj = bool(usuario.tipo_contrato and str(usuario.tipo_contrato).strip().upper() == 'PJ')
        except Exception:
            is_pj = False

        if not is_pj and getattr(usuario, 'pj_contratante', None):
            is_pj = True

        if is_pj and not aditivo:

            title = "TERMO DE ENTREGA E RESPONSABILIDADE PELO USO DE EQUIPAMENTOS"
            elements.append(Paragraph(title, style_title))

            campos_template = [
                "Contratante: _________________________________________________",
                "CNPJ: ______________________________________________________",
                "Endereço: ___________________________________________________",
                "Contratada: __________________________________________________",
                "CPF/CNPJ: __________________________________________________",
                "Data do Contrato de Prestação de Serviços (se aplicável): _____________________"
            ]

            valores = [
                valor_texto(
                    termo.empresa,
                    usuario.pj_contratante or usuario.empresa
                ),
                valor_texto(
                    termo.cnpj,
                    usuario.pj_contratante_cnpj or usuario.cnpj
                ),
                valor_texto(
                    termo.endereco,
                    usuario.pj_contratante_endereco or usuario.endereco
                ),
                valor_texto(
                    termo.nome_colaborador,
                    usuario.pj_contratada or usuario.username
                ),
                valor_texto(
                    termo.cpf_cnpj,
                    usuario.pj_contratada_cnpj or usuario.cpf
                ),
                valor_data(
                    termo.data_admissao or usuario.pj_data_contrato or usuario.data_admissao
                )
            ]

            for tpl, val in zip(campos_template, valores):

                if val and val != '':
                    new_line = re.sub(
                        r'_{2,}',
                        lambda m: val,
                        tpl,
                        count=1
                    )
                else:
                    new_line = tpl

                elements.append(Paragraph(new_line, style_normal))

            texto1 = """
<b>1. OBJETO</b><br/><br/>

O presente Termo tem por objeto formalizar a entrega, posse e responsabilidade da Contratada quanto ao uso,
guarda, conservação e devolução dos equipamentos, dispositivos, acessórios e demais bens de propriedade da
Contratante, fornecidos para a execução de sua prestação de serviços, em razão dos sistemas de gestão e
infraestruturas que estes comportam.
"""

            elements.append(Paragraph(texto1, style_normal))

            texto2 = """
<b>2. RESPONSABILIDADES DO COLABORADOR/TERCEIRO</b><br/><br/>

Ao assinar o presente Termo, a Contratante declara ciência e concordância com as seguintes políticas internas:<br/><br/>

I. Zelar pela integridade física e funcional dos equipamentos e acessórios recebidos, utilizando-os
com diligência e cuidado, exclusivamente para o desempenho de sua prestação de serviços, salvo
autorização expressa da Contratante.<br/><br/>

II. Utilizar os equipamentos de forma adequada e em conformidade com as orientações fornecidas
pela Contratante, abstendo-se de práticas que possam ocasionar danos, tais como quedas,
exposição à umidade, transporte inadequado ou instalações indevidas.<br/><br/>

III. Não compartilhar, ceder, emprestar ou permitir o uso dos equipamentos por terceiros não
autorizados, salvo mediante autorização prévia e expressa da Contratante.<br/><br/>

IV. Não instalar, copiar ou utilizar softwares, programas ou aplicações sem a devida autorização da
Contratante, especialmente aqueles sem licença ou em desconformidade com a legislação vigente,
ficando ciente de que eventuais irregularidades poderão ensejar a adoção de medidas cabíveis.<br/><br/>

V. Observar rigorosamente as políticas internas da Contratante relacionadas à segurança da
informação, proteção de dados e uso de recursos tecnológicos, mantendo o sigilo sobre
quaisquer dados, informações ou acessos obtidos em razão da utilização dos equipamentos.<br/><br/>

VI. Não compartilhar credenciais de acesso, senhas ou quaisquer mecanismos de autenticação
vinculados aos sistemas corporativos.<br/><br/>

VII. Comunicar imediatamente à Contratante a ocorrência de qualquer defeito, dano, perda, extravio,
furto, roubo ou incidente envolvendo os equipamentos e dados, colaborando com a apuração dos
fatos.<br/><br/>

VIII. Devolver os equipamentos nas condições previstas neste Termo, quando do encerramento do
contrato de prestação de serviços ou sempre que solicitado pela Contratante.<br/><br/>

Parágrafo único. A Contratada somente será responsabilizada por danos causados aos equipamentos quando
comprovada a ocorrência de dolo ou culpa (negligência, imprudência ou imperícia), não se incluindo hipóteses
de desgaste natural decorrente do uso regular, nem situações de caso fortuito ou força maior, devidamente
comprovadas.
"""

            elements.append(Paragraph(texto2, style_normal))

            texto3 = """
<b>3. POLÍTICAS DE USO E SEGURANÇA DIGITAL</b><br/><br/>

A Contratada declara estar ciente e concorda em cumprir integralmente as políticas internas da Contratante
relacionadas ao uso de equipamentos, segurança da informação e proteção de dados, comprometendo-se a
observar, em especial, as seguintes diretrizes:<br/><br/>

I. Utilizar os equipamentos fornecidos em conformidade com as normas internas da Contratante,
abstendo-se de qualquer uso indevido, ilícito ou em desacordo com sua prestação de serviço.<br/><br/>

II. Observar as diretrizes relativas à segurança da informação, incluindo, mas não se limitando, à
proteção de dados corporativos, confidenciais e pessoais, nos termos da Lei Geral de Proteção de
Dados Pessoais.<br/><br/>

III. Não copiar, reproduzir, armazenar, compartilhar ou transferir, por qualquer meio, informações da
Contratante em dispositivos pessoais ou de terceiros, sem prévia e expressa autorização da
Contratante.<br/><br/>

IV. Adotar boas práticas de segurança digital, incluindo a utilização adequada de senhas, bloqueio de
dispositivos, atualização de sistemas e prevenção contra acessos não autorizados.<br/><br/>

V. Não acessar, armazenar ou compartilhar conteúdos ilícitos, impróprios ou que possam
comprometer a segurança dos sistemas e da rede corporativa.<br/><br/>

VI. Permitir, quando solicitado, a realização de auditorias, verificações ou monitoramento nos
equipamentos, para fins de segurança da informação, compliance e proteção de ativos da
Contratante, observada a legislação aplicável, incluindo a LGPD, e respeitando a intimidade da
Contratada, bem como os princípios da transparência e proporcionalidade.<br/><br/>

Parágrafo primeiro. A Contratada reconhece que os equipamentos fornecidos pela Contratante são
ferramentas para realização de sua prestação de serviços, em razão dos sistemas de gestão e infraestruturas que
estes comportam, e não devem ser usados para fins pessoais (armazenamento de fotos, arquivos pessoais, e-mails privados, etc).<br/><br/>
<br/>
Parágrafo segundo. O descumprimento das disposições previstas neste item poderá ensejar a adoção de
medidas disciplinares, sem prejuízo da responsabilização civil e, quando aplicável, administrativa e penal.
"""

            elements.append(Paragraph(texto3, style_normal))

            texto4 = """
<b>4. CONDIÇÕES DE DEVOLUÇÃO</b><br/><br/>

No ato da devolução, a Contratante realizará a conferência e inspeção dos equipamentos e acessórios entregues
à Contratada, a fim de verificar seu estado de conservação e funcionamento.<br/><br/>

Parágrafo primeiro. Os equipamentos deverão ser devolvidos em condições compatíveis com o uso regular,
ressalvados os desgastes naturais decorrentes da utilização normal.<br/><br/>

Parágrafo segundo. Caso seja constatada a existência de danos, ausência de itens, defeitos ou avarias, a
Contratante procederá à apuração das circunstâncias, a fim de verificar eventual responsabilidade da
Contratada, especialmente nos casos de dolo ou culpa (negligência, imprudência ou imperícia).<br/><br/>

Parágrafo terceiro. Constatada a responsabilidade da Contratada, esta poderá ser obrigada ao ressarcimento
dos prejuízos causados, limitado ao valor necessário ao reparo ou reposição do bem, observado o disposto nas
demais disposições deste Termo.<br/><br/>

Parágrafo quarto. A Contratada deverá comunicar imediatamente à Contratante a ocorrência de perda,
extravio, furto, roubo ou qualquer incidente envolvendo os equipamentos, apresentando, quando aplicável, o
respectivo boletim de ocorrência ou documentação comprobatória.<br/><br/>

Parágrafo quinto. Na hipótese de encerramento do contrato de prestação de serviços, os equipamentos
deverão ser devolvidos imediatamente ou em prazo razoável a ser definido pela Contratante, mediante
solicitação formal.<br/><br/>

Parágrafo sexto. Enquanto não realizada a devolução dos equipamentos ou a regularização de eventuais
pendências identificadas, permanecem válidas todas as obrigações previstas neste Termo.
"""

            elements.append(Paragraph(texto4, style_normal))

            texto5 = """
<b>5. AUTORIZAÇÃO DE DESCONTO</b><br/><br/>

Através do presente Termo, a Contratada autoriza expressamente que a Contratante realize o desconto dos
valores correspondentes aos prejuízos causados aos equipamentos e/ou acessórios sob sua responsabilidade,
desde que comprovadamente decorrentes de dolo ou culpa (negligência, imprudência ou imperícia), tais como:
mau uso, extravio, perda, não devolução ou danos evitáveis, sobre os valores de eventuais obrigações em
aberto de dias trabalhados e não faturados.<br/><br/>

Parágrafo primeiro. O desconto será limitado ao valor efetivamente apurado para reparo ou reposição do
bem, vedada qualquer cobrança superior ao prejuízo comprovado.<br/><br/>

Parágrafo segundo. A realização de qualquer desconto estará condicionada à prévia apuração dos fatos pela
Contratante, sendo assegurado à Contratada o direito de apresentar esclarecimentos e defesa antes da efetivação
do desconto.<br/><br/>

Parágrafo terceiro. Fica expressamente ressalvado que não serão passíveis de desconto os danos decorrentes
do desgaste natural pelo uso regular do equipamento ou de caso fortuito e força maior, desde que devidamente
comprovados.<br/><br/>

Parágrafo quarto. Na hipótese de encerramento do contrato de prestação de serviços, permanecendo pendente
a devolução dos equipamentos ou a apuração de eventuais danos, a Contratada autoriza o desconto dos valores
correspondentes sobre os valores de eventuais obrigações em aberto de dias trabalhados e não faturados.
"""

            elements.append(Paragraph(texto5, style_normal))

            texto6 = """
<b>6. VIGÊNCIA</b><br/><br/>

O presente Termo entra em vigor na data de sua assinatura e permanecerá válido por prazo indeterminado,
enquanto a Contratada estiver de posse de quaisquer equipamentos, acessórios ou dispositivos fornecidos pela
Contratante, independentemente de substituição, atualização ou entrega adicional, inclusive aquelas
formalizadas por meio de aditivos.<br/><br/>

Parágrafo primeiro. As obrigações de guarda, zelo, uso adequado, sigilo e devolução dos equipamentos
subsistirão durante todo o período em que a Contratada permanecer na posse dos bens, inclusive em casos de
afastamento, suspensão ou encerramento da relação contratual.<br/><br/>

Parágrafo segundo. Na hipótese de encerramento da relação contratual, as obrigações previstas neste Termo
permanecerão válidas até a efetiva devolução de todos os equipamentos.
"""

            elements.append(Paragraph(texto6, style_normal))

            texto7 = """
<b>7. ASSINATURA ELETRÔNICA</b><br/><br/>

Este documento poderá firmado por meio de assinatura eletrônica avançada ou qualificada, em conformidade com
a Lei Federal nº 14.063/2020. Nesse sentido, a assinatura deste documento pressupõe declarada, de forma
inequívoca, a concordância do(s) declarante(s), sendo um compromisso vinculante, válido, eficaz e executável,
em todos os seus termos, condições e cláusulas, de acordo com o Artigo 10, Parágrafo 2º da Medida Provisória nº
2.200-2/2001 e do Artigo 6º do Decreto 10.278/2020. Por fim, ainda que algum dos signatários venha a assinar
digitalmente este documento em local e/ou data diversa da estabelecida, o local e a data de celebração deste
documento são, para todos os fins, aqueles abaixo indicados, sendo que este documento produzirá efeitos a partir
da data nele indicada.
"""

            elements.append(Paragraph(texto7, style_normal))

            texto8 = """
<b>8. FORO</b><br/><br/>

Para dirimir eventuais dúvidas oriundas deste Termo, as partes elegem o foro da comarca de Campinas/SP,
com renúncia a qualquer outro, por mais privilegiado que seja.
"""

            elements.append(Paragraph(texto8, style_normal))

            elements.append(
                Paragraph(
                    "<b>9. EQUIPAMENTOS ENTREGUES</b>",
                    style_section
                )
            )

            texto9 = """
A Contratante declara ter fornecido os seguintes itens à Contratada, elencada no preâmbulo:
"""

            elements.append(Paragraph(texto9, style_normal))

            table = Table(
                table_data,
                colWidths=[
                    5 * cm,
                    2.5 * cm,
                    2.5 * cm,
                    2.5 * cm,
                    2.5 * cm,
                    3 * cm
                ]
            )

            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))

            elements.append(table)

            elements.append(Spacer(1, 20))

            checklist = """
<b>10. CHECKLIST DE ENTREGA</b><br/><br/>

Considerando o disposto na cláusula anterior, a Contratada declara, nesta data e por meio do checklist abaixo
colacionado, ter recebido, na presente data, os seguintes itens de propriedade da Contratada, para uso exclusivo
da prestação de serviços:<br/><br/>

· ☐ Notebook (ServiceTag): ____________________________________<br/>
· ☐ Fonte de alimentação / Carregador do notebook: ____________________________________<br/>
· ☐ Monitor externo adicional (ServiceTag): ___________________________________<br/>
· ☐ Teclado ( ) USB ( ) Sem fio: ____________________________________<br/>
· ☐ Mouse ( ) USB ( ) Sem fio: ____________________________________<br/>
· ☐ Mouse Pad: ____________________________________<br/>
· ☐ Fone de ouvido com microfone (Headset): ____________________________________<br/>
· ☐ Celular corporativo (Nº de IMEI): ____________________________________<br/>
· ☐ Chip SIM instalado (Nº da Linha/Operadora): ____________________________________<br/>
· ☐ Cabo e carregador do celular: ____________________________________<br/>
· ☐ Adaptadores de vídeo ou Hubs de dados: ____________________________________<br/>
· ☐ Mochila ou estojo de proteção para transporte: ____________________________________<br/>
· ☐ Funcionamento do hardware e periféricos testado e validado? ( ) Sim ( ) Não<br/>
· ☐ Demais acessórios / Outros (especificar): ____________________________________
"""

            elements.append(Paragraph(checklist, style_normal))

            texto_final = """
<b>11. DECLARAÇÃO FINAL</b><br/><br/>

A Contratada declara, para todos os fins de direito, que recebeu os equipamentos e/ou acessórios descritos
neste Termo em perfeitas condições de uso e funcionamento, após conferência, comprometendo-se a cumprir
integralmente todas as obrigações relativas à sua utilização, guarda, conservação e devolução.<br/><br/>

Declara, ainda, que leu, compreendeu e concorda, por livre e espontânea vontade, com todas as cláusulas e
condições estabelecidas neste Termo, bem como com as políticas internas da Contratante à ela relacionadas,
especialmente aquelas relativas à segurança da informação e à proteção de dados.<br/><br/>

Local e Data: _________________________________________________
"""

            elements.append(Paragraph(texto_final, style_normal))

            elements.append(Spacer(1, 30))

            tabela_assinaturas = Table(
                [
                    [
                        "Assinatura da Contratada",
                        "Assinatura da Contratante"
                    ],
                    [
                        "________________________________",
                        "________________________________"
                    ]
                ],
                colWidths=[8 * cm, 8 * cm]
            )

            tabela_assinaturas.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 20),
                ('TOPPADDING', (0, 1), (-1, 1), 10),
            ]))

            elements.append(tabela_assinaturas)

            blocos_fotos = _blocos_fotos_em_uma_pagina(equipamentos)
            if blocos_fotos:
                elements.append(PageBreak())
                elements.append(Paragraph('FOTOS DOS EQUIPAMENTOS', style_section))
                elements.extend(blocos_fotos)

            doc.build(elements)

            if nome_arquivo:
                return nome_arquivo

            buffer.seek(0)
            return buffer
            '''
                            Paragraph(
                                "<b>9. EQUIPAMENTOS ENTREGUES</b>",
                                style_section
                            )
                        )

                        texto9 = """
            A Contratante declara ter fornecido os seguintes itens à Contratada, elencada no preâmbulo:
            """

                        elements.append(Paragraph(texto9, style_normal))

                        table = Table(
                            table_data,
                            colWidths=[
                                5 * cm,
                                2.5 * cm,
                                2.5 * cm,
                                2.5 * cm,
                                2.5 * cm,
                                3 * cm
                            ]
                        )

                        table.setStyle(TableStyle([
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 9),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                            ('TOPPADDING', (0, 1), (-1, -1), 10),
                            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                        ]))

                        elements.append(table)
                        elements.append(Spacer(1, 20))

                        checklist = """
            <b>10. CHECKLIST DE ENTREGA</b><br/><br/>

            Considerando o disposto na cláusula anterior, a Contratada declara, nesta data e por meio do checklist abaixo
            colacionado, ter recebido, na presente data, os seguintes itens de propriedade da Contratada, para uso exclusivo
            da prestação de serviços:<br/><br/>

            · ☐ Notebook (ServiceTag): ____________________________________<br/>
            · ☐ Fonte de alimentação / Carregador do notebook: ____________________________________<br/>
            · ☐ Monitor externo adicional (ServiceTag): ___________________________________<br/>
            · ☐ Teclado ( ) USB ( ) Sem fio: ____________________________________<br/>
            · ☐ Mouse ( ) USB ( ) Sem fio: ____________________________________<br/>
            · ☐ Mouse Pad: ____________________________________<br/>
            · ☐ Fone de ouvido com microfone (Headset): ____________________________________<br/>
            · ☐ Celular corporativo (Nº de IMEI): ____________________________________<br/>
            · ☐ Chip SIM instalado (Nº da Linha/Operadora): ____________________________________<br/>
            · ☐ Cabo e carregador do celular: ____________________________________<br/>
            · ☐ Adaptadores de vídeo ou Hubs de dados: ____________________________________<br/>
            · ☐ Mochila ou estojo de proteção para transporte: ____________________________________<br/>
            · ☐ Funcionamento do hardware e periféricos testado e validado? ( ) Sim ( ) Não<br/>
            · ☐ Demais acessórios / Outros (especificar): ____________________________________
            """

                        elements.append(Paragraph(checklist, style_normal))

                        texto_final = """
            <b>11. DECLARAÇÃO FINAL</b><br/><br/>

            A Contratada declara, para todos os fins de direito, que recebeu os equipamentos e/ou acessórios descritos
            neste Termo em perfeitas condições de uso e funcionamento, após conferência, comprometendo-se a cumprir
            integralmente todas as obrigações relativas à sua utilização, guarda, conservação e devolução.<br/><br/>

            Declara, ainda, que leu, compreendeu e concorda, por livre e espontânea vontade, com todas as cláusulas e
            condições estabelecidas neste Termo, bem como com as políticas internas da Contratante à ela relacionadas,
            especialmente aquelas relativas à segurança da informação e à proteção de dados.<br/><br/>

            Local e Data: _________________________________________________
            """

                        elements.append(Paragraph(texto_final, style_normal))

                        elements.append(Spacer(1, 30))

                        tabela_assinaturas = Table(
                            [
                                [
                                    "Assinatura da Contratada",
                                    "Assinatura da Contratante"
                                ],
                                [
                                    "________________________________",
                                    "________________________________"
                                ]
                            ],
                            colWidths=[8 * cm, 8 * cm]
                        )

                        tabela_assinaturas.setStyle(TableStyle([
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 0), (-1, -1), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 20),
                            ('TOPPADDING', (0, 1), (-1, 1), 10),
                        ]))

                        elements.append(tabela_assinaturas)

                        blocos_fotos = _blocos_fotos_em_uma_pagina(equipamentos)
                        if blocos_fotos:
                            elements.append(PageBreak())
                            elements.append(Paragraph('FOTOS DOS EQUIPAMENTOS', style_section))
                            elements.extend(blocos_fotos)
            '''
        # ADITIVO
        # =========================================================

        if aditivo:
            title = "ADITIVO AO TERMO DE ENTREGA E RESPONSABILIDADE PELO USO DE EQUIPAMENTOS"
            elements.append(Paragraph(title, style_title))

            campos_template = [
                "Contratante: _________________________________________________",
                "CNPJ: ______________________________________________________",
                "Endereço: ___________________________________________________",
                "Contratada: __________________________________________________",
                "CPF/CNPJ: __________________________________________________",
                "Data do Contrato de Prestação de Serviços (se aplicável): _____________________"
            ]

            valores = [
                valor_texto(usuario.pj_contratante, usuario.empresa),
                valor_texto(usuario.pj_contratante_cnpj, usuario.cnpj),
                valor_texto(usuario.pj_contratante_endereco, usuario.endereco),
                valor_texto(usuario.pj_contratada or usuario.username, usuario.username),
                valor_texto(usuario.pj_contratada_cnpj, usuario.cpf),
                valor_data(usuario.pj_data_contrato or usuario.data_admissao)
            ]

            for tpl, val in zip(campos_template, valores):

                if val and val != '':
                    new_line = re.sub(
                        r'_{2,}',
                        lambda m: val,
                        tpl,
                        count=1
                    )
                else:
                    new_line = tpl

                elements.append(Paragraph(new_line, style_normal))

            texto1 = """
<b>1. OBJETO</b><br/><br/>

O presente Aditivo tem por objeto formalizar a entrega adicional de equipamentos, dispositivos,
acessórios e demais bens de propriedade da Contratante, fornecidos para a execução da prestação
de serviços da Contratada, em razão dos sistemas de gestão e infraestruturas que estes comportam,
bem como regulamentar a responsabilidade da Contratada quanto ao uso, guarda, conservação,
sigilo e devolução dos respectivos bens, complementando o Termo de Responsabilidade anteriormente
firmado entre as partes.
"""

            elements.append(Paragraph(texto1, style_normal))

            texto2 = """
<b>2. RESPONSABILIDADE</b><br/><br/>

A Contratada declara estar ciente de que os equipamentos, dispositivos e acessórios descritos neste
Aditivo passam a integrar, para todos os fins de direito, o Termo de Entrega e Responsabilidade pelo
Uso de Equipamentos anteriormente firmado entre as partes, submetendo-se integralmente às mesmas
regras, condições, obrigações e políticas ali previstas.<br/><br/>

A Contratada compromete-se a utilizar os itens exclusivamente para a execução de sua prestação de
serviços, responsabilizando-se pela guarda, zelo e conservação dos bens recebidos, abstendo-se de
qualquer utilização indevida, compartilhamento não autorizado ou prática que possa ocasionar danos
aos equipamentos.<br/><br/>

Parágrafo primeiro. A Contratada será responsabilizada apenas pelos danos comprovadamente
decorrentes de dolo ou culpa (negligência, imprudência ou imperícia), incluindo hipóteses de mau uso,
extravio, perda, danos evitáveis ou não devolução injustificada dos equipamentos.<br/><br/>

Parágrafo segundo. Não serão considerados de responsabilidade da Contratada os danos decorrentes
do desgaste natural pelo uso regular dos equipamentos, bem como aqueles resultantes de caso fortuito
ou força maior, devidamente comprovados.
"""

            elements.append(Paragraph(texto2, style_normal))

            texto3 = """
<b>3. DEVOLUÇÃO</b><br/><br/>

Os equipamentos e acessórios descritos neste Aditivo deverão ser devolvidos nas mesmas condições
estabelecidas no Termo principal anteriormente firmado, juntamente com os demais bens utilizados
pela Contratada na execução da prestação de serviços, sempre que solicitado pela Contratante ou
quando do encerramento da relação contratual.<br/><br/>

Parágrafo primeiro. No ato da devolução, os itens serão submetidos à conferência e inspeção,
observando-se os mesmos critérios previstos no Termo principal, para verificação do estado de
conservação, funcionamento e integridade dos equipamentos.<br/><br/>

Parágrafo segundo. Eventuais danos, ausência de itens, defeitos, irregularidades ou avarias serão
apurados pela Contratante, a fim de verificar eventual responsabilidade da Contratada, observadas as
disposições contratuais e legais aplicáveis.<br/><br/>

Parágrafo terceiro. Permanecem integralmente aplicáveis aos equipamentos descritos neste Aditivo
todas as regras referentes à devolução, responsabilização e eventual ressarcimento previstas no Termo
principal anteriormente firmado entre as partes.
"""

            elements.append(Paragraph(texto3, style_normal))

            texto4 = """
<b>4. ASSINATURA ELETRÔNICA</b><br/><br/>

Este documento poderá firmado por meio de assinatura eletrônica avançada ou qualificada, em conformidade com
a Lei Federal nº 14.063/2020. Nesse sentido, a assinatura deste documento pressupõe declarada, de forma
inequívoca, a concordância do(s) declarante(s), sendo um compromisso vinculante, válido, eficaz e executável,
em todos os seus termos, condições e cláusulas, de acordo com o Artigo 10, Parágrafo 2º da Medida Provisória nº
2.200-2/2001 e do Artigo 6º do Decreto 10.278/2020. Por fim, ainda que algum dos signatários venha a assinar
digitalmente este documento em local e/ou data diversa da estabelecida, o local e a data de celebração deste
documento são, para todos os fins, aqueles abaixo indicados, sendo que este documento produzirá efeitos a partir
da data nele indicada.
"""

            elements.append(Paragraph(texto4, style_normal))

            elements.append(
                Paragraph(
                    "<b>5. ITENS ADICIONAIS ENTREGUES</b>",
                    style_section
                )
            )

            texto5 = """
A Contratante declara ter fornecido os seguintes itens adicionais à Contratada, elencada no preâmbulo:
"""

            elements.append(Paragraph(texto5, style_normal))

            table = Table(
                table_data,
                colWidths=[
                    5 * cm,
                    2.5 * cm,
                    2.5 * cm,
                    2.5 * cm,
                    2.5 * cm,
                    3 * cm
                ]
            )

            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))

            elements.append(table)

            elements.append(Spacer(1, 20))

            checklist = """
<b>6. CHECKLIST DE ENTREGA DE EQUIPAMENTOS ADICIONAIS</b><br/><br/>

Considerando o disposto na cláusula anterior, a Contratada declara, nesta data e por meio do checklist
abaixo colacionado, ter recebido os seguintes itens adicionais de propriedade da Contratante, para
uso exclusivo na prestação de serviços, em complemento aos equipamentos anteriormente entregues:<br/><br/>

· ☐ Notebook (ServiceTag): ____________________________________<br/>
· ☐ Fonte de alimentação / Carregador do notebook: ____________________________________<br/>
· ☐ Monitor externo adicional (ServiceTag): ___________________________________<br/>
· ☐ Teclado ( ) USB ( ) Sem fio: ____________________________________<br/>
· ☐ Mouse ( ) USB ( ) Sem fio: ____________________________________<br/>
· ☐ Mouse Pad: ____________________________________<br/>
· ☐ Suporte para notebook: ____________________________________<br/>
· ☐ Fone de ouvido com microfone (Headset): ____________________________________<br/>
· ☐ Celular corporativo (Nº de IMEI): ____________________________________<br/>
· ☐ Chip SIM instalado (Nº da Linha/Operadora): ____________________________________<br/>
· ☐ Cabo e carregador do celular: ____________________________________<br/>
· ☐ Adaptadores de vídeo ou Hubs de dados: ____________________________________<br/>
· ☐ Mochila ou estojo de proteção para transporte: ____________________________________<br/>
· ☐ Funcionamento do hardware e periféricos testado e validado? ( ) Sim ( ) Não<br/>
· ☐ Demais acessórios / Outros (especificar): ____________________________________
"""

            elements.append(Paragraph(checklist, style_normal))

            texto_final = """
<b>7. DECLARAÇÃO FINAL</b><br/><br/>

A Contratada declara, para todos os fins de direito, que recebeu os equipamentos e/ou acessórios
descritos neste Aditivo em perfeitas condições de uso e funcionamento, após conferência,
comprometendo-se a cumprir integralmente todas as obrigações relativas à sua utilização, guarda,
conservação e devolução.<br/><br/>

Declara, ainda, que leu, compreendeu e concorda, por livre e espontânea vontade, com todas as
disposições constantes deste Aditivo, bem como com as cláusulas, políticas e obrigações previstas no
Termo de Entrega e Responsabilidade pelo Uso de Equipamentos anteriormente firmado.<br/><br/>

Ficam expressamente ratificadas e mantidas em pleno vigor todas as cláusulas, condições e obrigações
previstas no Termo principal, permanecendo este inalterado em tudo aquilo que não conflitar com o
presente instrumento, passando este Aditivo a integrá-lo para todos os fins de direito.<br/><br/>

Local e Data: _________________________________________________
"""

            elements.append(Paragraph(texto_final, style_normal))

            elements.append(Spacer(1, 30))

            tabela_assinaturas = Table(
                [
                    [
                        "Assinatura da Contratada",
                        "Assinatura da Contratante"
                    ],
                    [
                        "________________________________",
                        "________________________________"
                    ]
                ],
                colWidths=[8 * cm, 8 * cm]
            )

            tabela_assinaturas.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 20),
                ('TOPPADDING', (0, 1), (-1, 1), 10),
            ]))

            elements.append(tabela_assinaturas)

            blocos_fotos = _blocos_fotos_em_uma_pagina(equipamentos)
            if blocos_fotos:
                elements.append(PageBreak())
                elements.append(Paragraph('FOTOS DOS EQUIPAMENTOS ADICIONAIS', style_section))
                elements.append(Spacer(1, 12))
                elements.extend(blocos_fotos)

            doc.build(elements)

            if nome_arquivo:
                return nome_arquivo

            buffer.seek(0)
            return buffer

        # =========================================================
        # TERMO PJ (Pessoa Jurídica)
        # =========================================================
        is_pj = False
        try:
            is_pj = bool(usuario.tipo_contrato and str(usuario.tipo_contrato).strip().upper() == 'PJ')
        except Exception:
            is_pj = False

        # fallback: if PJ header fields exist, treat as PJ
        if not is_pj and getattr(usuario, 'pj_contratante', None):
            is_pj = True

        if is_pj:

            title = "TERMO DE ENTREGA E RESPONSABILIDADE PELO USO DE EQUIPAMENTOS - PESSOA JURÍDICA"
            elements.append(Paragraph(title, style_title))

            campos_template = [
                "Empresa:  _________________________________________________",
                "CNPJ:  ____________________________________________________",
                "Endereço:  _________________________________________________",
                "Colaborador: _______________________________________________",
                "Cargo/Função (se aplicável):  __________________________________",
                "CPF/CNPJ:  ________________________________________________",
                "Data de Admissão  (se aplicável): _______________________________",
                "Departamento (se aplicável): ___________________________________",
                "Local de trabalho (se aplicável): ________________________________"
            ]

            valores = [
                valor_texto(usuario.pj_contratante, termo.empresa),
                valor_texto(usuario.pj_contratante_cnpj, termo.cnpj),
                valor_texto(usuario.pj_contratante_endereco, termo.endereco),
                valor_texto(usuario.pj_contratada or termo.nome_colaborador or usuario.username, usuario.username),
                valor_texto(termo.cargo_funcao, usuario.cargo),
                valor_texto(usuario.pj_contratada_cnpj or termo.cpf_cnpj or usuario.cpf, usuario.cpf),
                valor_data(usuario.pj_data_contrato or termo.data_admissao or usuario.data_admissao),
                valor_texto(termo.departamento, usuario.departamento),
                valor_texto(termo.local_trabalho, usuario.local_trabalho)
            ]

            for tpl, val in zip(campos_template, valores):
                if val and val != '':
                    new_line = re.sub(r'_{2,}', lambda m: val, tpl, count=1)
                else:
                    new_line = tpl

                elements.append(Paragraph(new_line, style_normal))

            texto = """
<b>1. OBJETO</b><br/><br/>

O presente Termo tem por objeto formalizar a entrega, posse e responsabilidade da contratada/representante quanto ao uso, guarda, conservação e devolução dos equipamentos, dispositivos, acessórios e demais bens de propriedade da contratante, fornecidos para a execução de suas atividades profissionais.
"""

            elements.append(Paragraph(texto, style_normal))

            texto2 = """
<b>2. RESPONSABILIDADES DA CONTRATADA/REPRESENTANTE</b><br/><br/>

Ao assinar o presente Termo, a contratada/representante declara ciência e concordância com as seguintes políticas internas:<br/><br/>

I. Zelar pela integridade física e funcional dos equipamentos e acessórios recebidos, utilizando-os com diligência e cuidado, exclusivamente para o desempenho de suas atividades profissionais, salvo autorização expressa da contratante.<br/><br/>

II. Utilizar os equipamentos de forma adequada e em conformidade com as orientações fornecidas pela contratante, abstendo-se de práticas que possam ocasionar danos, tais como quedas, exposição à umidade, transporte inadequado ou instalações indevidas.<br/><br/>

III. Não compartilhar, ceder, emprestar ou permitir o uso dos equipamentos por terceiros não autorizados, salvo mediante autorização prévia e expressa da contratante.<br/><br/>

IV. Não instalar, copiar ou utilizar softwares, programas ou aplicações sem a devida autorização da contratante, especialmente aqueles sem licença ou em desconformidade com a legislação vigente, ficando ciente de que eventuais irregularidades poderão ensejar a adoção de medidas cabíveis.<br/><br/>

V. Observar rigorosamente as políticas internas da contratante relacionadas à segurança da informação, proteção de dados e uso de recursos tecnológicos, mantendo o sigilo sobre quaisquer dados, informações ou acessos obtidos em razão da utilização dos equipamentos.<br/><br/>

VI. Não compartilhar credenciais de acesso, senhas ou quaisquer mecanismos de autenticação vinculados aos sistemas corporativos.<br/><br/>

VII. Comunicar imediatamente à contratante a ocorrência de qualquer defeito, dano, perda, extravio, furto, roubo ou incidente envolvendo os equipamentos e dados, colaborando com a apuração dos fatos.<br/><br/>

VIII. Devolver os equipamentos nas condições previstas neste Termo, ao término da relação contratual ou sempre que solicitado pela contratante.<br/><br/>

Parágrafo único. A contratada/representante somente será responsabilizada por danos causados aos equipamentos quando comprovada a ocorrência de dolo ou culpa (negligência, imprudência ou imperícia), não se incluindo hipóteses de desgaste natural decorrente do uso regular, nem situações de caso fortuito ou força maior, devidamente comprovadas.
"""

            elements.append(Paragraph(texto2, style_normal))

            texto3 = """
<b>3. POLÍTICAS DE USO E SEGURANÇA DIGITAL</b><br/><br/>

A contratada/representante declara estar ciente e concorda em cumprir integralmente as políticas internas da contratante relacionadas ao uso de equipamentos, segurança da informação e proteção de dados, comprometendo-se a observar, em especial, as seguintes diretrizes:<br/><br/>

I. Utilizar os equipamentos corporativos em conformidade com as normas internas da contratante, abstendo-se de qualquer uso indevido, ilícito ou em desacordo com suas atividades profissionais.<br/><br/>

II. Observar as diretrizes relativas à segurança da informação, incluindo, mas não se limitando, à proteção de dados corporativos, confidenciais e pessoais, nos termos da Lei Geral de Proteção de Dados Pessoais.<br/><br/>

III. Não copiar, reproduzir, armazenar, compartilhar ou transferir, por qualquer meio, informações corporativas em dispositivos pessoais ou de terceiros, sem prévia e expressa autorização da contratante.<br/><br/>

IV. Adotar boas práticas de segurança digital, incluindo a utilização adequada de senhas, bloqueio de dispositivos, atualização de sistemas e prevenção contra acessos não autorizados.<br/><br/>

V. Não acessar, armazenar ou compartilhar conteúdos ilícitos, impróprios ou que possam comprometer a segurança dos sistemas e da rede corporativa.<br/><br/>

VI. Permitir, quando solicitado, a realização de auditorias, verificações ou monitoramento nos equipamentos corporativos, para fins de segurança da informação, compliance e proteção de ativos da contratante, observada a legislação aplicável, incluindo a LGPD, e respeitando a intimidade da contratada/representante, bem como os princípios da transparência e proporcionalidade.<br/><br/>

Parágrafo primeiro. A contratada/representante reconhece que os equipamentos fornecidos pela contratante são ferramentas de trabalho/para realização da atividade profissional e não devem ser usados para fins pessoais (armazenamento de fotos, arquivos pessoais, e-mails privados, etc).<br/><br/>

Parágrafo segundo. O descumprimento das disposições previstas neste item poderá ensejar a adoção de medidas disciplinares, sem prejuízo da responsabilização civil e, quando aplicável, administrativa e penal.
"""

            elements.append(Paragraph(texto3, style_normal))

            texto4 = """
<b>4. CONDIÇÕES DE DEVOLUÇÃO</b><br/><br/>

No ato da devolução, a contratante realizará a conferência e inspeção dos equipamentos e acessórios entregues à contratada/representante, a fim de verificar seu estado de conservação e funcionamento.<br/><br/>

Parágrafo primeiro. Os equipamentos deverão ser devolvidos em condições compatíveis com o uso regular, ressalvados os desgastes naturais decorrentes da utilização normal.<br/><br/>

Parágrafo segundo. Caso seja constatada a existência de danos, ausência de itens, defeitos ou avarias, a empresa procederá à apuração das circunstâncias, a fim de verificar eventual responsabilidade do colaborador, especialmente nos casos de dolo ou culpa (negligência, imprudência ou imperícia).<br/><br/>

Parágrafo terceiro. Constatada a responsabilidade da contratada/representante, esta poderá ser obrigada ao ressarcimento dos prejuízos causados, limitado ao valor necessário ao reparo ou reposição do bem, observado o disposto neste Termo e na legislação aplicável.<br/><br/>

Parágrafo quarto. A contratada/representante deverá comunicar imediatamente à contratante a ocorrência de perda, extravio, furto, roubo ou qualquer incidente envolvendo os equipamentos, apresentando, quando aplicável, o respectivo boletim de ocorrência ou documentação comprobatória.<br/><br/>

Parágrafo quinto. Na hipótese de encerramento da relação contratual, os equipamentos deverão ser devolvidos imediatamente ou em prazo razoável a ser definido pela contratante, mediante solicitação formal.<br/><br/>

Parágrafo sexto. Enquanto não realizada a devolução dos equipamentos ou a regularização de eventuais pendências identificadas, permanecem válidas todas as obrigações previstas neste Termo.
"""

            elements.append(Paragraph(texto4, style_normal))

            texto5 = """
<b>5. RESSARCIMENTO</b><br/><br/>

A contratada/representante autoriza expressamente a contratante a cobrar e/ou compensar valores correspondentes a prejuízos causados aos equipamentos e/ou acessórios sob sua responsabilidade, desde que comprovadamente decorrentes de dolo ou culpa (negligência, imprudência ou imperícia), tais como: mau uso, extravio, perda, não devolução ou danos evitáveis.<br/><br/>

Parágrafo primeiro. O ressarcimento será limitado ao valor efetivamente apurado para reparo ou reposição do bem, vedada qualquer cobrança superior ao prejuízo comprovado.<br/><br/>

Parágrafo segundo. A realização de qualquer cobrança estará condicionada à prévia apuração dos fatos pela contratante, sendo assegurado à contratada/representante o direito de apresentar esclarecimentos e defesa antes da efetivação da cobrança.<br/><br/>

Parágrafo terceiro. Fica expressamente ressalvado que não serão passíveis de cobrança os danos decorrentes do desgaste natural pelo uso regular do equipamento ou de caso fortuito e força maior, desde que devidamente comprovados.<br/><br/>

Parágrafo quarto. Na hipótese de encerramento da relação contratual, permanecendo pendente a devolução dos equipamentos ou a apuração de eventuais danos, a contratada/representante autoriza a cobrança dos valores correspondentes, observado o limite legal e sem prejuízo das demais medidas cabíveis.
"""

            elements.append(Paragraph(texto5, style_normal))

            texto6 = """
<b>6. VIGÊNCIA</b><br/><br/>

O presente Termo entra em vigor na data de sua assinatura e permanecerá válido por prazo indeterminado, enquanto a contratada/representante estiver de posse de quaisquer equipamentos, acessórios ou dispositivos fornecidos pela contratante, independentemente de substituição, atualização ou entrega adicional, inclusive aquelas formalizadas por meio de aditivos.<br/><br/>

Parágrafo primeiro. As obrigações de guarda, zelo, uso adequado, sigilo e devolução dos equipamentos subsistirão durante todo o período em que a contratada/representante permanecer na posse dos bens, inclusive em casos de suspensão, interrupção ou encerramento da relação contratual.<br/><br/>

Parágrafo segundo. Na hipótese de encerramento da relação contratual, as obrigações previstas neste Termo permanecerão válidas até a efetiva devolução de todos os equipamentos.
"""

            elements.append(Paragraph(texto6, style_normal))

            texto7 = """
<b>7. ASSINATURA ELETRÔNICA</b><br/><br/>

Este documento poderá firmado por meio de assinatura eletrônica avançada ou qualificada, em conformidade com a Lei Federal nº 14.063/2020. Nesse sentido, a assinatura deste documento pressupõe declarada, de forma inequívoca, a concordância do(s) declarante(s), sendo um compromisso vinculante, válido, eficaz e executável, em todos os seus termos, condições e cláusulas, de acordo com o Artigo 10, Parágrafo 2º da Medida Provisória nº 2.200-2/2001 e do Artigo 6º do Decreto 10.278/2020. Por fim, ainda que algum dos signatários venha a assinar digitalmente este documento em local e/ou data diversa da estabelecida, o local e a data de celebração deste documento são, para todos os fins, aqueles abaixo indicados, sendo que este documento produzirá efeitos a partir da data nele indicada.
"""

            elements.append(Paragraph(texto7, style_normal))

            texto8 = """
<b>8. FORO</b><br/><br/>

Para dirimir eventuais dúvidas oriundas deste Termo, as partes elegem o foro da comarca de Campinas/SP, com renúncia a qualquer outro, por mais privilegiado que seja.
"""

            elements.append(Paragraph(texto8, style_normal))

            elements.append(Paragraph("<b>9. EQUIPAMENTOS ENTREGUES</b>", style_section))

            texto9 = """
A empresa declara ter fornecido os seguintes itens ao colaborador, elencado no preâmbulo:
"""

            elements.append(Paragraph(texto9, style_normal))

            table = Table(
                table_data,
                colWidths=[5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm]
            )

            table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('TOPPADDING', (0,1), (-1,-1), 10),
                ('BOTTOMPADDING', (0,1), (-1,-1), 10),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 20))

            checklist = """
<b>10. CHECKLIST DE ENTREGA</b><br/><br/>

Considerando o disposto na cláusula anterior, o colaborador declara, nesta data e por meio do checklist abaixo colacionado, ter recebido, na presente data, os seguintes itens de propriedade da empresa, para uso exclusivamente profissional:<br/><br/>

·        [ ] Notebook (ServiceTag): ____________________________________<br/>
·        [ ] Fonte de alimentação / Carregador do notebook: ____________________________________<br/>
·        [ ] Monitor externo adicional (ServiceTag): ___________________________________<br/>
·        [ ] Teclado ( ) USB ( ) Sem fio: ____________________________________<br/>
·        [ ] Mouse ( ) USB ( ) Sem fio: ____________________________________<br/>
·        [ ] Mouse Pad: ____________________________________<br/>
·        [ ] Suporte para notebook: ____________________________________<br/>
·        [ ] Fone de ouvido com microfone (Headset): ____________________________________<br/>
·        [ ] Celular corporativo (Nº de IMEI): ____________________________________<br/>
·        [ ] Chip SIM instalado (Nº da Linha/Operadora): ____________________________________<br/>
·        [ ] Cabo e carregador do celular: ____________________________________<br/>
·        [ ] Adaptadores de vídeo ou Hubs de dados: ____________________________________<br/>
·        [ ] Mochila ou estojo de proteção para transporte: ____________________________________<br/>
·        [ ] Funcionamento do hardware e periféricos testado e validado? ( ) Sim ( ) Não<br/>
·        [ ] Demais acessórios / Outros (especificar): ____________________________________
"""

            elements.append(Paragraph(checklist, style_normal))

            texto_final = """
<b>11. DECLARAÇÃO FINAL</b><br/><br/>

O colaborador declara, para todos os fins de direito, que recebeu os equipamentos e/ou acessórios descritos neste Termo em perfeitas condições de uso e funcionamento, após conferência, comprometendo-se a cumprir integralmente todas as obrigações relativas à sua utilização, guarda, conservação e devolução.<br/><br/>

Declara, ainda, que leu, compreendeu e concorda, por livre e espontânea vontade, com todas as cláusulas e condições estabelecidas neste Termo, bem como com as políticas internas da empresa a ele relacionadas, especialmente aquelas relativas à segurança da informação e à proteção de dados.<br/><br/>

Local e Data: _________________________________________________
"""

            elements.append(Paragraph(texto_final, style_normal))

            elements.append(Spacer(1, 30))

            tabela_assinaturas = Table(
                [
                    [
                        "Assinatura do Colaborador/Terceiro",
                        "Assinatura da Empresa"
                    ],
                    [
                        "________________________________",
                        "________________________________"
                    ]
                ],
                colWidths=[8*cm, 8*cm]
            )

            tabela_assinaturas.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 20),
                ('TOPPADDING', (0, 1), (-1, 1), 10),
            ]))

            elements.append(tabela_assinaturas)

            blocos_fotos = _blocos_fotos_em_uma_pagina(equipamentos)
            if blocos_fotos:
                elements.append(PageBreak())
                elements.append(Paragraph('FOTOS DOS EQUIPAMENTOS', style_section))
                elements.extend(blocos_fotos)

            doc.build(elements)

            if nome_arquivo:
                return nome_arquivo

            buffer.seek(0)
            return buffer

        # =========================================================
        # TERMO PRINCIPAL (updated template)
        # =========================================================

        title = "TERMO DE ENTREGA E RESPONSABILIDADE PELO USO DE EQUIPAMENTOS DA EMPRESA"
        elements.append(Paragraph(title, style_title))

        campos_template = [
            "Empresa:  _________________________________________________",
            "CNPJ:  ____________________________________________________",
            "Endereço:  _________________________________________________",
            "Colaborador: _______________________________________________",
            "Cargo/Função (se aplicável):  __________________________________",
            "CPF/CNPJ:  ________________________________________________",
            "Data de Admissão  (se aplicável): _______________________________",
            "Departamento (se aplicável): ___________________________________",
            "Local de trabalho (se aplicável): ________________________________"
        ]

        valores = [
            valor_texto(termo.empresa, usuario.empresa),
            valor_texto(termo.cnpj, usuario.cnpj),
            valor_texto(termo.endereco, usuario.endereco),
            valor_texto(termo.nome_colaborador, usuario.username),
            valor_texto(termo.cargo_funcao, usuario.cargo),
            valor_texto(termo.cpf_cnpj, usuario.cpf),
            valor_data(termo.data_admissao or usuario.data_admissao),
            valor_texto(termo.departamento, usuario.departamento),
            valor_texto(termo.local_trabalho, usuario.local_trabalho)
        ]

        for tpl, val in zip(campos_template, valores):
            if val and val != '':
                new_line = re.sub(r'_{2,}', lambda m: val, tpl, count=1)
            else:
                new_line = tpl

            elements.append(Paragraph(new_line, style_normal))

        texto = """
<b>1. OBJETO</b><br/><br/>

O presente Termo tem por objeto formalizar a entrega, posse e responsabilidade do colaborador quanto ao uso, guarda, conservação e devolução dos equipamentos, dispositivos, acessórios e demais bens de propriedade da empresa, fornecidos para a execução de suas atividades profissionais.
"""

        elements.append(Paragraph(texto, style_normal))

        texto2 = """
<b>2. RESPONSABILIDADES DO COLABORADOR/TERCEIRO</b><br/><br/>

Ao assinar o presente Termo, o colaborador declara ciência e concordância com as seguintes políticas internas:<br/><br/>

I. Zelar pela integridade física e funcional dos equipamentos e acessórios recebidos, utilizando-os com diligência e cuidado, exclusivamente para o desempenho de suas atividades profissionais, salvo autorização expressa da empresa.<br/><br/>

II. Utilizar os equipamentos de forma adequada e em conformidade com as orientações fornecidas pela empresa, abstendo-se de práticas que possam ocasionar danos, tais como quedas, exposição à umidade, transporte inadequado ou instalações indevidas.<br/><br/>

III. Não compartilhar, ceder, emprestar ou permitir o uso dos equipamentos por terceiros não autorizados, salvo mediante autorização prévia e expressa da empresa.<br/><br/>

IV. Não instalar, copiar ou utilizar softwares, programas ou aplicações sem a devida autorização da empresa, especialmente aqueles sem licença ou em desconformidade com a legislação vigente, ficando ciente de que eventuais irregularidades poderão ensejar a adoção de medidas cabíveis.<br/><br/>

V. Observar rigorosamente as políticas internas da empresa relacionadas à segurança da informação, proteção de dados e uso de recursos tecnológicos, mantendo o sigilo sobre quaisquer dados, informações ou acessos obtidos em razão da utilização dos equipamentos.<br/><br/>

VI. Não compartilhar credenciais de acesso, senhas ou quaisquer mecanismos de autenticação vinculados aos sistemas corporativos.<br/><br/>

VII. Comunicar imediatamente à empresa a ocorrência de qualquer defeito, dano, perda, extravio, furto, roubo ou incidente envolvendo os equipamentos e dados, colaborando com a apuração dos fatos.<br/><br/>

VIII. Devolver os equipamentos nas condições previstas neste Termo, ao término do vínculo empregatício ou sempre que solicitado pela empresa.<br/><br/>

Parágrafo único. O colaborador somente será responsabilizado por danos causados aos equipamentos quando comprovada a ocorrência de dolo ou culpa (negligência, imprudência ou imperícia), não se incluindo hipóteses de desgaste natural decorrente do uso regular, nem situações de caso fortuito ou força maior, devidamente comprovadas.
"""

        elements.append(Paragraph(texto2, style_normal))

        texto3 = """
<b>3. POLÍTICAS DE USO E SEGURANÇA DIGITAL</b><br/><br/>

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

        elements.append(Paragraph(texto3, style_normal))

        texto4 = """
<b>4. CONDIÇÕES DE DEVOLUÇÃO</b><br/><br/>

No ato da devolução, a empresa realizará a conferência e inspeção dos equipamentos e acessórios entregues ao colaborador, a fim de verificar seu estado de conservação e funcionamento.<br/><br/>

Parágrafo primeiro. Os equipamentos deverão ser devolvidos em condições compatíveis com o uso regular, ressalvados os desgastes naturais decorrentes da utilização normal.<br/><br/>

Parágrafo segundo. Caso seja constatada a existência de danos, ausência de itens, defeitos ou avarias, a empresa procederá à apuração das circunstâncias, a fim de verificar eventual responsabilidade do colaborador, especialmente nos casos de dolo ou culpa (negligência, imprudência ou imperícia).<br/><br/>

Parágrafo terceiro. Constatada a responsabilidade do colaborador, este poderá ser obrigado ao ressarcimento dos prejuízos causados, limitado ao valor necessário ao reparo ou reposição do bem, observado o disposto no artigo 462 da Consolidação das Leis do Trabalho e demais disposições deste Termo.<br/><br/>

Parágrafo quarto. O colaborador deverá comunicar imediatamente à empresa a ocorrência de perda, extravio, furto, roubo ou qualquer incidente envolvendo os equipamentos, apresentando, quando aplicável, o respectivo boletim de ocorrência ou documentação comprobatória.<br/><br/>

Parágrafo quinto. Na hipótese de desligamento, os equipamentos deverão ser devolvidos imediatamente ou em prazo razoável a ser definido pela empresa, mediante solicitação formal.<br/><br/>

Parágrafo sexto. Enquanto não realizada a devolução dos equipamentos ou a regularização de eventuais pendências identificadas, permanecem válidas todas as obrigações previstas neste Termo.
"""

        elements.append(Paragraph(texto4, style_normal))

        texto5 = """
<b>5. AUTORIZAÇÃO DE DESCONTO</b><br/><br/>

O colaborador, nos termos do artigo 462 da Consolidação das Leis do Trabalho, autoriza expressamente a empresa a proceder ao desconto em folha de pagamento de valores correspondentes a prejuízos causados aos equipamentos e/ou acessórios sob sua responsabilidade, desde que comprovadamente decorrentes de dolo ou culpa (negligência, imprudência ou imperícia), tais como: mau uso, extravio, perda, não devolução ou danos evitáveis.<br/><br/>

Parágrafo primeiro. O desconto será limitado ao valor efetivamente apurado para reparo ou reposição do bem, vedada qualquer cobrança superior ao prejuízo comprovado.<br/><br/>

Parágrafo segundo. A realização de qualquer desconto estará condicionada à prévia apuração dos fatos pela empresa, sendo assegurado ao colaborador o direito de apresentar esclarecimentos e defesa antes da efetivação do desconto.<br/><br/>

Parágrafo terceiro. Fica expressamente ressalvado que não serão passíveis de desconto os danos decorrentes do desgaste natural pelo uso regular do equipamento ou de caso fortuito e força maior, desde que devidamente comprovados.<br/><br/>

Parágrafo quarto. Na hipótese de rescisão contratual, permanecendo pendente a devolução dos equipamentos ou a apuração de eventuais danos, o colaborador autoriza o desconto dos valores correspondentes nas verbas rescisórias, observado o limite legal e sem prejuízo das verbas de natureza alimentar.
"""

        elements.append(Paragraph(texto5, style_normal))

        texto6 = """
<b>6. VIGÊNCIA</b><br/><br/>

O presente Termo entra em vigor na data de sua assinatura e permanecerá válido por prazo indeterminado, enquanto o colaborador estiver de posse de quaisquer equipamentos, acessórios ou dispositivos fornecidos pela empresa, independentemente de substituição, atualização ou entrega adicional, inclusive aquelas formalizadas por meio de aditivos.<br/><br/>

Parágrafo primeiro. As obrigações de guarda, zelo, uso adequado, sigilo e devolução dos equipamentos subsistirão durante todo o período em que o colaborador permanecer na posse dos bens, inclusive em casos de afastamento, suspensão ou interrupção do contrato de trabalho.<br/><br/>

Parágrafo segundo. Na hipótese de rescisão do contrato de trabalho, as obrigações previstas neste Termo permanecerão válidas até a efetiva devolução de todos os equipamentos.
"""

        elements.append(Paragraph(texto6, style_normal))

        texto7 = """
<b>7. ASSINATURA ELETRÔNICA</b><br/><br/>

Este documento poderá firmado por meio de assinatura eletrônica avançada ou qualificada, em conformidade com a Lei Federal nº 14.063/2020. Nesse sentido, a assinatura deste documento pressupõe declarada, de forma inequívoca, a concordância do(s) declarante(s), sendo um compromisso vinculante, válido, eficaz e executável, em todos os seus termos, condições e cláusulas, de acordo com o Artigo 10, Parágrafo 2º da Medida Provisória nº 2.200-2/2001 e do Artigo 6º do Decreto 10.278/2020. Por fim, ainda que algum dos signatários venha a assinar digitalmente este documento em local e/ou data diversa da estabelecida, o local e a data de celebração deste documento são, para todos os fins, aqueles abaixo indicados, sendo que este documento produzirá efeitos a partir da data nele indicada.
"""

        elements.append(Paragraph(texto7, style_normal))

        texto8 = """
<b>8. FORO</b><br/><br/>

Para dirimir eventuais dúvidas oriundas deste Termo, as partes elegem o foro da comarca do local da prestação de serviços do colaborador, nos termos do artigo 651 da Consolidação das Leis do Trabalho.<br/><br/>

Parágrafo único. Sem prejuízo do disposto no caput, para as hipóteses que não se enquadrem na competência da Justiça do Trabalho ou ainda quando inexistente conflito com as regras legais de competência, fica eleito o foro da comarca de Campinas/SP, com renúncia a qualquer outro, por mais privilegiado que seja.
"""

        elements.append(Paragraph(texto8, style_normal))

        elements.append(Paragraph("<b>9. EQUIPAMENTOS ENTREGUES</b>", style_section))

        texto9 = """
A empresa declara ter fornecido os seguintes itens ao colaborador, elencado no preâmbulo:
"""

        elements.append(Paragraph(texto9, style_normal))

        table = Table(
            table_data,
            colWidths=[5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm]
        )

        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('TOPPADDING', (0,1), (-1,-1), 10),
            ('BOTTOMPADDING', (0,1), (-1,-1), 10),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        checklist = """
<b>10. CHECKLIST DE ENTREGA</b><br/><br/>

Considerando o disposto na cláusula anterior, o colaborador declara, nesta data e por meio do checklist abaixo colacionado, ter recebido, na presente data, os seguintes itens de propriedade da empresa, para uso exclusivamente profissional:<br/><br/>

·        [ ] Notebook (ServiceTag): ____________________________________<br/>
·        [ ] Fonte de alimentação / Carregador do notebook: ____________________________________<br/>
·        [ ] Monitor externo adicional (ServiceTag): ___________________________________<br/>
·        [ ] Teclado ( ) USB ( ) Sem fio: ____________________________________<br/>
·        [ ] Mouse ( ) USB ( ) Sem fio: ____________________________________<br/>
·        [ ] Mouse Pad: ____________________________________<br/>
·        [ ] Suporte para notebook: ____________________________________<br/>
·        [ ] Fone de ouvido com microfone (Headset): ____________________________________<br/>
·        [ ] Celular corporativo (Nº de IMEI): ____________________________________<br/>
·        [ ] Chip SIM instalado (Nº da Linha/Operadora): ____________________________________<br/>
·        [ ] Cabo e carregador do celular: ____________________________________<br/>
·        [ ] Adaptadores de vídeo ou Hubs de dados: ____________________________________<br/>
·        [ ] Mochila ou estojo de proteção para transporte: ____________________________________<br/>
·        [ ] Funcionamento do hardware e periféricos testado e validado? ( ) Sim ( ) Não<br/>
·        [ ] Demais acessórios / Outros (especificar): ____________________________________
"""

        elements.append(Paragraph(checklist, style_normal))

        texto_final = """
<b>11. DECLARAÇÃO FINAL</b><br/><br/>

O colaborador declara, para todos os fins de direito, que recebeu os equipamentos e/ou acessórios descritos neste Termo em perfeitas condições de uso e funcionamento, após conferência, comprometendo-se a cumprir integralmente todas as obrigações relativas à sua utilização, guarda, conservação e devolução.<br/><br/>

Declara, ainda, que leu, compreendeu e concorda, por livre e espontânea vontade, com todas as cláusulas e condições estabelecidas neste Termo, bem como com as políticas internas da empresa a ele relacionadas, especialmente aquelas relativas à segurança da informação e à proteção de dados.<br/><br/>

Local e Data: _________________________________________________
"""

        elements.append(Paragraph(texto_final, style_normal))

        elements.append(Spacer(1, 30))

        tabela_assinaturas = Table(
            [
                [
                    "Assinatura do Colaborador/Terceiro",
                    "Assinatura da Empresa"
                ],
                [
                    "________________________________",
                    "________________________________"
                ]
            ],
            colWidths=[8*cm, 8*cm]
        )

        tabela_assinaturas.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 20),
            ('TOPPADDING', (0, 1), (-1, 1), 10),
        ]))

        elements.append(tabela_assinaturas)

        blocos_fotos = _blocos_fotos_em_uma_pagina(equipamentos)
        if blocos_fotos:
            elements.append(PageBreak())
            elements.append(Paragraph('FOTOS DOS EQUIPAMENTOS', style_section))
            elements.extend(blocos_fotos)

        doc.build(elements)

        if nome_arquivo:
            return nome_arquivo

        buffer.seek(0)
        return buffer
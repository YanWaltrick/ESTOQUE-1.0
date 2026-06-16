import os
import sys
import unicodedata
import xlrd

sys.path.insert(0, os.getcwd())
from app import create_app
from app.models import User

path = 'Cópia de Cópia de Lista_Ativos1169.xls'
wb = xlrd.open_workbook(path)
sheet = wb.sheet_by_index(0)
header_row = None
for i in range(sheet.nrows):
    row = [str(v).strip().lower() for v in sheet.row_values(i)]
    if any('cpf' in v or 'funcionário' in v or 'funcionario' in v for v in row):
        header_row = i
        break
if header_row is None:
    raise RuntimeError('Não encontrei cabeçalho')

headers = [str(v).strip() for v in sheet.row_values(header_row)]
rows = []
for i in range(header_row + 1, sheet.nrows):
    row = [sheet.cell_value(i, j) for j in range(sheet.ncols)]
    if any(str(v).strip() for v in row):
        rows.append(row)

app = create_app()
with app.app_context():
    names = []
    for row in rows:
        nome = ''
        if 'Funcionário' in headers:
            nome = str(row[headers.index('Funcionário')]).strip()
        elif 'Funcionario' in headers:
            nome = str(row[headers.index('Funcionario')]).strip()
        if nome:
            names.append(nome)

    existing = []
    missing = []
    for nome in names:
        username = ''.join(ch for ch in unicodedata.normalize('NFD', nome).lower() if unicodedata.category(ch) != 'Mn')
        if User.query.filter_by(username=username).first():
            existing.append(nome)
        else:
            missing.append(nome)

    print('Total nomes:', len(names))
    print('Existentes:', len(existing))
    print('Ausentes:', len(missing))
    print('Exemplos ausentes:', missing[:20])

from pathlib import Path
path = Path('database.py')
text = path.read_text(encoding='utf-8')
needle = "    # Inicializar banco de dados\n    db.init_app(app)\n\n    return app, db\n"
print('found', needle in text)
print('index', text.find(needle))
if needle in text:
    print('snippet:', repr(text[text.find(needle):text.find(needle)+len(needle)]))

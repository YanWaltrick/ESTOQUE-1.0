import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import create_app, db
from app.models import DocumentoUsuario

def _pasta_documentos():
    from flask import current_app
    pasta = os.path.join(current_app.root_path, '..', 'static', 'uploads', 'documentos')
    return os.path.abspath(pasta)

def main():
    app,_,_ = create_app()
    missing = []
    with app.app_context():
        docs = DocumentoUsuario.query.all()
        pasta = _pasta_documentos()
        for d in docs:
            path = os.path.join(pasta, d.arquivo)
            if not os.path.exists(path):
                missing.append((d.id_documento, d.arquivo))

    if missing:
        print('Missing files:', len(missing))
        for m in missing:
            print(m)
    else:
        print('All files present for', len(docs), 'documents.')

if __name__ == '__main__':
    main()

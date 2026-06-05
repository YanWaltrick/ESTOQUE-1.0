import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import create_app, db
from app.models import DocumentoUsuario, User

def main():
    app,_,_ = create_app()
    with app.app_context():
        docs = DocumentoUsuario.query.order_by(DocumentoUsuario.data_criacao.desc()).all()
        for d in docs:
            user = User.query.get(d.id_usuario)
            print(d.id_documento, d.id_usuario, user.username if user else None, d.nome_documento, d.arquivo, d.data_criacao)

if __name__ == '__main__':
    main()

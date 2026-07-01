#!/usr/bin/env python3
"""Migra arquivos de `static/uploads/documentos/` para a tabela `documentos_arquivos` no banco.

Cria a tabela se não existir e insere cada arquivo como BLOB.
Uso:
  python scripts/migrate_docs_to_db.py [--delete]

--delete : remove os arquivos originais após migração bem-sucedida
"""

import argparse
import datetime
import mimetypes
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.database import create_app, db

# Reutiliza o modelo canônico em vez de redefinir a tabela inline (a redefinição
# colide com o `DocumentoArquivo` já registrado ao importar o pacote `app`).
from app.models import DocumentoArquivo


def main(delete_files: bool):
    app, _db, _mail = create_app()

    # A pasta de uploads fica na raiz do projeto, não em `scripts/`.
    uploads_dir = os.path.join(PROJECT_ROOT, "static", "uploads", "documentos")

    if not os.path.isdir(uploads_dir):
        print(f"Pasta de uploads não encontrada: {uploads_dir}")
        sys.exit(1)

    with app.app_context():
        # cria tabela quando necessário
        db.create_all()

        files = sorted(os.listdir(uploads_dir))
        if not files:
            print("Nenhum arquivo encontrado em", uploads_dir)
            return

        migrated = 0
        for fname in files:
            path = os.path.join(uploads_dir, fname)
            if not os.path.isfile(path):
                continue

            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception as e:
                print(f"Erro lendo {path}: {e}")
                continue

            size = len(data)
            mime = mimetypes.guess_type(path)[0] or "application/octet-stream"

            # evitar duplicatas (mesmo nome e tamanho)
            exists = db.session.execute(
                db.select(DocumentoArquivo).filter_by(filename=fname, size=size)
            ).scalar_one_or_none()

            if exists:
                print(f"Skipping existing: {fname}")
                continue

            novo = DocumentoArquivo(
                filename=fname,
                content=data,
                mime_type=mime,
                size=size,
                uploaded_at=datetime.datetime.utcnow(),
            )
            db.session.add(novo)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Erro inserindo {fname}: {e}")
                continue

            migrated += 1

            if delete_files:
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Erro removendo {path}: {e}")

            print(f"Migrated: {fname} ({size} bytes)")

        print(f"Done. Migrated {migrated} files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate documents into DB")
    parser.add_argument(
        "--delete", action="store_true", help="Delete original files after successful migration"
    )
    args = parser.parse_args()

    main(args.delete)

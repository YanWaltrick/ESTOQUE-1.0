import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text

from app.database import create_app, db


def main():
    app, _, _ = create_app()
    with app.app_context():
        try:
            db.session.execute(
                text("ALTER TABLE documentos_arquivos MODIFY COLUMN content LONGBLOB")
            )
            db.session.commit()
            print("ALTER OK")
        except Exception as e:
            print("ALTER ERROR:", e)


if __name__ == "__main__":
    main()

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import create_app, db
from sqlalchemy import text

def main():
    app,_,_ = create_app()
    with app.app_context():
        cnt = db.session.execute(text('select count(*) from documentos_arquivos')).scalar()
        print('COUNT', cnt)

if __name__ == '__main__':
    main()

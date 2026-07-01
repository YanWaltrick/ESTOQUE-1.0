#!/usr/bin/env python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import db
from app.models import User

UPDATED_FIELDS = {
    "cnpj": "31.508.560/0001-85",
    "endereco": "Av Doutor José Bonifácio Coutinho, 150, 8º andar, Jardim Madalena, SP/Campinas",
    "area": "Antares Securitizadora de Recebíveis Comerciais S.A.",
    "localizacao": "Av Doutor José Bonifácio Coutinho, 150, 8º andar, Jardim Madalena, SP/Campinas",
    "local_trabalho": "Campinas - Presencial",
}

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        usuarios = User.query.filter(User.role != "admin").all()
        count = 0
        for usuario in usuarios:
            for field, value in UPDATED_FIELDS.items():
                setattr(usuario, field, value)
            count += 1
        db.session.commit()
        print(f"Atualizados {count} usuários (exceto admin).")

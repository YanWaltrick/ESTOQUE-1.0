#!/usr/bin/env python
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import db
from app.models import User

DOMAIN = "somaasset.com.br"


def normalize_username(value):
    text = str(value or "").strip()
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.lower()
    return text


def build_email_from_name(name):
    normalized = normalize_username(name)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    if not tokens:
        return ""
    first = tokens[0]
    last = tokens[-1] if len(tokens) > 1 else tokens[0]
    return f"{first}.{last}@{DOMAIN}"


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        users = User.query.filter(User.role != "admin").all()
        updated = 0
        for user in users:
            email = build_email_from_name(user.username)
            if email:
                user.email = email
                updated += 1
        db.session.commit()
        print(f"Atualizados {updated} usuários com emails @somaasset.com.br")

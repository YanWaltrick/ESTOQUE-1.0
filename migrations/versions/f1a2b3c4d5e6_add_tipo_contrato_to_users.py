"""add tipo_contrato to users

Revision ID: f1a2b3c4d5e6
Revises: 69d8e3f9c4d7
Create Date: 2026-05-21 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '69d8e3f9c4d7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col['name'] for col in inspector.get_columns('users')}

    if 'tipo_contrato' not in existing_columns:
        op.add_column('users', sa.Column('tipo_contrato', sa.String(length=10), nullable=False, server_default=sa.text("'CLT'")))
    op.execute("UPDATE users SET tipo_contrato = 'CLT' WHERE tipo_contrato IS NULL OR tipo_contrato = ''")


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col['name'] for col in inspector.get_columns('users')}
    if 'tipo_contrato' in existing_columns:
        op.drop_column('users', 'tipo_contrato')

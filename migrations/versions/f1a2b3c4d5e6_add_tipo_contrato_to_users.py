"""add tipo_contrato to users

Revision ID: f1a2b3c4d5e6
Revises: 69d8e3f9c4d7
Create Date: 2026-05-21 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '69d8e3f9c4d7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('tipo_contrato', sa.String(length=10), nullable=False, server_default=sa.text("'CLT'")))
    op.execute("UPDATE users SET tipo_contrato = 'CLT' WHERE tipo_contrato IS NULL OR tipo_contrato = ''")


def downgrade():
    op.drop_column('users', 'tipo_contrato')

"""add email to users

Revision ID: g1a2b3c4d5e6
Revises: f1a2b3c4d5e6
Create Date: 2026-05-28 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'g1a2b3c4d5e6'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col['name'] for col in inspector.get_columns('users')}

    if 'email' not in existing_columns:
        op.add_column('users', sa.Column('email', sa.String(length=150), nullable=True, server_default=''))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col['name'] for col in inspector.get_columns('users')}
    if 'email' in existing_columns:
        op.drop_column('users', 'email')

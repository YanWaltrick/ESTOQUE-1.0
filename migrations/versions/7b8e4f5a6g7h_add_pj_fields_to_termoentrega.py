"""Add PJ fields to TermoEntrega model

Revision ID: 7b8e4f5a6g7h
Revises: a1b2c3d4e5f6
Create Date: 2026-05-27 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '7b8e4f5a6g7h'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add PJ fields to termos_entrega table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Get list of columns in termos_entrega table
    columns = [col['name'] for col in inspector.get_columns('termos_entrega')]
    
    # Add PJ fields if they don't exist
    if 'pj_contratante' not in columns:
        op.add_column('termos_entrega', sa.Column('pj_contratante', sa.String(255), nullable=True, server_default=''))
    
    if 'pj_contratante_cnpj' not in columns:
        op.add_column('termos_entrega', sa.Column('pj_contratante_cnpj', sa.String(18), nullable=True, server_default=''))
    
    if 'pj_contratante_endereco' not in columns:
        op.add_column('termos_entrega', sa.Column('pj_contratante_endereco', sa.String(500), nullable=True, server_default=''))
    
    if 'pj_contratada' not in columns:
        op.add_column('termos_entrega', sa.Column('pj_contratada', sa.String(255), nullable=True, server_default=''))
    
    if 'pj_contratada_cnpj' not in columns:
        op.add_column('termos_entrega', sa.Column('pj_contratada_cnpj', sa.String(18), nullable=True, server_default=''))
    
    if 'pj_data_contrato' not in columns:
        op.add_column('termos_entrega', sa.Column('pj_data_contrato', sa.Date(), nullable=True))


def downgrade() -> None:
    """Remove PJ fields from termos_entrega table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Get list of columns in termos_entrega table
    columns = [col['name'] for col in inspector.get_columns('termos_entrega')]
    
    # Remove PJ fields if they exist
    if 'pj_contratante' in columns:
        op.drop_column('termos_entrega', 'pj_contratante')
    
    if 'pj_contratante_cnpj' in columns:
        op.drop_column('termos_entrega', 'pj_contratante_cnpj')
    
    if 'pj_contratante_endereco' in columns:
        op.drop_column('termos_entrega', 'pj_contratante_endereco')
    
    if 'pj_contratada' in columns:
        op.drop_column('termos_entrega', 'pj_contratada')
    
    if 'pj_contratada_cnpj' in columns:
        op.drop_column('termos_entrega', 'pj_contratada_cnpj')
    
    if 'pj_data_contrato' in columns:
        op.drop_column('termos_entrega', 'pj_data_contrato')

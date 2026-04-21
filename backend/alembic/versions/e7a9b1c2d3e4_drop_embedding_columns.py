"""drop embedding columns from files and issues

Revision ID: e7a9b1c2d3e4
Revises: a1b2c3d4e5f6
Create Date: 2026-04-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7a9b1c2d3e4'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('issues', schema=None) as batch_op:
        batch_op.drop_column('embedding_updated_at')
        batch_op.drop_column('embedding_error')
        batch_op.drop_column('embedding_status')

    with op.batch_alter_table('project_files', schema=None) as batch_op:
        batch_op.drop_column('embedding_updated_at')
        batch_op.drop_column('embedding_error')
        batch_op.drop_column('embedding_status')


def downgrade() -> None:
    with op.batch_alter_table('project_files', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embedding_status', sa.String(length=20), nullable=False, server_default='pending'))
        batch_op.add_column(sa.Column('embedding_error', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('embedding_updated_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('issues', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embedding_status', sa.String(length=20), nullable=False, server_default='pending'))
        batch_op.add_column(sa.Column('embedding_error', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('embedding_updated_at', sa.DateTime(), nullable=True))

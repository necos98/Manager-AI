"""add favorited_at to projects

Revision ID: e3b028c8b53a
Revises: 5922b9fdc87a
Create Date: 2026-05-27 16:59:09.513521

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b028c8b53a'
down_revision: Union[str, None] = '5922b9fdc87a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('favorited_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('favorited_at')

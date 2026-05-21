"""add_category_to_issues

Revision ID: f75dc9e9f3ff
Revises: 3ed109d6a415
Create Date: 2026-05-21 15:17:42.801951

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f75dc9e9f3ff'
down_revision: Union[str, None] = '3ed109d6a415'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('issues') as batch_op:
        batch_op.add_column(sa.Column('category', sa.String(50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('issues') as batch_op:
        batch_op.drop_column('category')

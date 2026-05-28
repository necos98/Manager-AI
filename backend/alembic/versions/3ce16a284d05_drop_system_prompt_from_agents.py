"""drop system_prompt from agents

Revision ID: 3ce16a284d05
Revises: fcc417cf56ab
Create Date: 2026-05-28 10:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ce16a284d05'
down_revision: Union[str, None] = 'fcc417cf56ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.drop_column('system_prompt')


def downgrade() -> None:
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('system_prompt', sa.Text(), nullable=False, server_default='')
        )

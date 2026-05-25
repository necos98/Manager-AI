"""add terminal_id to agent_step_runs

Revision ID: 072a542ac08c
Revises: f75dc9e9f3ff
Create Date: 2026-05-21 18:08:23.808323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '072a542ac08c'
down_revision: Union[str, None] = 'f75dc9e9f3ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('agent_step_runs', sa.Column('terminal_id', sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column('agent_step_runs', 'terminal_id')

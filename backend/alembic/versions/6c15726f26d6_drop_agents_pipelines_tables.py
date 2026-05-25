"""drop_agents_pipelines_tables

Revision ID: 6c15726f26d6
Revises: 072a542ac08c
Create Date: 2026-05-25 16:19:27.547484

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6c15726f26d6'
down_revision: Union[str, None] = '072a542ac08c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('agent_step_runs')
    op.drop_table('pipeline_runs')
    op.drop_table('agent_messages')
    op.drop_table('pipelines')
    op.drop_table('agents')


def downgrade() -> None:
    # These tables cannot be recreated from migration data alone.
    # This is intentional — the agents/pipeline feature has been permanently removed.
    pass

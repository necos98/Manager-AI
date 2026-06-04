"""add rejection_count to pipeline_runs and REJECTED status

Revision ID: ea6dc15a673d
Revises: ea6dc15a673c
Create Date: 2026-06-04 10:06:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea6dc15a673d'
down_revision: Union[str, None] = 'ea6dc15a673c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column("rejection_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("pipeline_runs", "rejection_count")

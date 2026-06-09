"""drop orchestrated column from pipeline_runs

Revision ID: a9b8c7d6e5f4
Revises: f9e8d7c6b5a4
Create Date: 2026-06-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, None] = "f9e8d7c6b5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("pipeline_runs", "orchestrated")


def downgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column("orchestrated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )

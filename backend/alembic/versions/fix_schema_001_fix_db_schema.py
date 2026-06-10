"""fix db schema: add missing columns rejection_count, intent; drop system_prompt

This migration brings the SQLite schema in sync with the SQLAlchemy models
after an earlier metadata.create_all() stamped the DB as head without actually
running the migration chain.

Adds:
  - pipeline_runs.rejection_count (Integer, default 0)
  - agents.intent (Text, default '')

Drops:
  - agents.system_prompt (Text)

Revision ID: fix_schema_001
Revises: 8cbf6da8b8c2
Create Date: 2026-06-10 22:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fix_schema_001"
down_revision: Union[str, None] = "8cbf6da8b8c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add rejection_count to pipeline_runs (missing from chain)
    with op.batch_alter_table("pipeline_runs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("rejection_count", sa.Integer(), nullable=False, server_default=sa.text("0"))
        )

    # Add intent to agents and drop system_prompt (both missing from chain)
    with op.batch_alter_table("agents", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("intent", sa.Text(), nullable=False, server_default="")
        )
        batch_op.drop_column("system_prompt")


def downgrade() -> None:
    with op.batch_alter_table("pipeline_runs", schema=None) as batch_op:
        batch_op.drop_column("rejection_count")

    with op.batch_alter_table("agents", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("system_prompt", sa.Text(), nullable=True)
        )
        batch_op.drop_column("intent")

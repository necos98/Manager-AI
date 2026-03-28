"""add terminal_command condition column

Revision ID: cc3dd4ee5ff6
Revises: bb2cc3dd4ee5
Create Date: 2026-03-28 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "cc3dd4ee5ff6"
down_revision: Union[str, None] = "bb2cc3dd4ee5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "terminal_commands",
        sa.Column("condition", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("terminal_commands", "condition")

"""remove provider column from agents

Revision ID: f9e8d7c6b5a4
Revises: eb34150b2a6b
Create Date: 2026-06-08 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f9e8d7c6b5a4"
down_revision: Union[str, None] = "eb34150b2a6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("agents", "provider")


def downgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="claude"),
    )

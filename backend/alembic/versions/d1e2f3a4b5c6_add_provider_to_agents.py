"""add provider column to agents

Revision ID: d1e2f3a4b5c6
Revises: b0c1d2e3f4a6
Create Date: 2026-06-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "b0c1d2e3f4a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="claude"),
    )


def downgrade() -> None:
    op.drop_column("agents", "provider")

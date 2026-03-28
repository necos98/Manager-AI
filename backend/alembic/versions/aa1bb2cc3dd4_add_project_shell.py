"""add project shell column

Revision ID: aa1bb2cc3dd4
Revises: de00ebdfc1c2
Create Date: 2026-03-28 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "aa1bb2cc3dd4"
down_revision: Union[str, None] = "de00ebdfc1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("shell", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "shell")

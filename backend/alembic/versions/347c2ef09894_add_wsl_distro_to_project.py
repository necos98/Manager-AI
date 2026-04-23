"""add_wsl_distro_to_project

Revision ID: 347c2ef09894
Revises: a2b3c4d5e6f7
Create Date: 2026-04-23 09:42:19.912517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '347c2ef09894'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("wsl_distro", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "wsl_distro")

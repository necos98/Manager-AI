"""add tech_stack to projects

Revision ID: 7bc067397cd0
Revises: 55bc4073dd1c
Create Date: 2026-03-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7bc067397cd0'
down_revision: Union[str, None] = '55bc4073dd1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('tech_stack', sa.Text(), nullable=False, server_default=sa.text("''")))


def downgrade() -> None:
    op.drop_column('projects', 'tech_stack')

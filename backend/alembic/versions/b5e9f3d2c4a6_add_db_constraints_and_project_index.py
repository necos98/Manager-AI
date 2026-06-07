"""add unique constraint on agent name and project name index

Revision ID: b5e9f3d2c4a6
Revises: fa326b3a9bb1
Create Date: 2026-06-07 09:11:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5e9f3d2c4a6'
down_revision: Union[str, None] = 'fa326b3a9bb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agent model unique constraint
    with op.batch_alter_table("agents") as batch_op:
        batch_op.create_unique_constraint("uq_agent_name", ["name"])

    # Project model index
    op.create_index("ix_projects_name", "projects", ["name"])


def downgrade() -> None:
    # Project model index
    op.drop_index("ix_projects_name", table_name="projects")

    # Agent model unique constraint
    with op.batch_alter_table("agents") as batch_op:
        batch_op.drop_constraint("uq_agent_name", type_="unique")

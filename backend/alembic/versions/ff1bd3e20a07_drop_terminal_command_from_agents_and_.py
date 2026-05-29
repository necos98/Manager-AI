"""drop terminal_command from agents and pipeline_steps

Revision ID: ff1bd3e20a07
Revises: 71a3c99abdae
Create Date: 2026-05-29 11:12:19.314330

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ff1bd3e20a07'
down_revision: Union[str, None] = '71a3c99abdae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE agents DROP COLUMN terminal_command")
    op.execute("ALTER TABLE pipeline_steps DROP COLUMN terminal_command")


def downgrade() -> None:
    op.execute("ALTER TABLE agents ADD COLUMN terminal_command TEXT NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE pipeline_steps ADD COLUMN terminal_command TEXT NOT NULL DEFAULT ''")

"""add queue entry fields: retry_count, last_terminal_id, status_changed_at

Revision ID: d4f5a6b7c8d5
Revises: fix_schema_001
Create Date: 2026-06-11 00:01:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f5a6b7c8d5'
down_revision: Union[str, None] = 'fix_schema_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('queue_entries', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('last_terminal_id', sa.String(length=36), nullable=True)
        )
        batch_op.add_column(
            sa.Column('status_changed_at', sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('queue_entries', schema=None) as batch_op:
        batch_op.drop_column('status_changed_at')
        batch_op.drop_column('last_terminal_id')
        batch_op.drop_column('retry_count')

"""migrate queue entry status values: DISPATCHING→RUNNING, DISPATCHED→DONE

Revision ID: d5e6f7a8b9c0
Revises: d4f5a6b7c8d5
Create Date: 2026-06-11 00:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'd4f5a6b7c8d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix any previously-migrated lowercase values (idempotent safety step)
    op.execute(
        "UPDATE queue_entries SET status = 'RUNNING' WHERE status = 'running'"
    )
    op.execute(
        "UPDATE queue_entries SET status = 'DONE' WHERE status = 'done'"
    )
    # Primary migration: rename old status names to new ones
    op.execute(
        "UPDATE queue_entries SET status = 'RUNNING' WHERE status = 'DISPATCHING'"
    )
    op.execute(
        "UPDATE queue_entries SET status = 'DONE' WHERE status = 'DISPATCHED'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE queue_entries SET status = 'DISPATCHING' WHERE status = 'RUNNING'"
    )
    op.execute(
        "UPDATE queue_entries SET status = 'DISPATCHED' WHERE status = 'DONE'"
    )

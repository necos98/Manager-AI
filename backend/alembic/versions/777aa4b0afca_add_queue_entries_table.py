"""add queue_entries table

Revision ID: 777aa4b0afca
Revises: a9b8c7d6e5f4
Create Date: 2026-06-10 00:07:51.089234

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '777aa4b0afca'
down_revision: Union[str, None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('queue_entries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('issue_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'DISPATCHING', 'DISPATCHED', 'FAILED',
                    name='queueentrystatus'),
            nullable=False,
        ),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'),
                  nullable=False),
        sa.Column('dispatched_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('queue_entries', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_queue_entries_issue_id'), ['issue_id'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_queue_entries_project_id'), ['project_id'],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('queue_entries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_queue_entries_project_id'))
        batch_op.drop_index(batch_op.f('ix_queue_entries_issue_id'))
    op.drop_table('queue_entries')

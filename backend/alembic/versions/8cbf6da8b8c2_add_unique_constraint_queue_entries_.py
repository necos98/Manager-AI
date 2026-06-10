"""add_unique_constraint_queue_entries_project_order

Revision ID: 8cbf6da8b8c2
Revises: 777aa4b0afca
Create Date: 2026-06-10 21:36:24.626665

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cbf6da8b8c2'
down_revision: Union[str, None] = '777aa4b0afca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('queue_entries', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_queue_entries_project_order',
            ['project_id', 'order'],
        )


def downgrade() -> None:
    with op.batch_alter_table('queue_entries', schema=None) as batch_op:
        batch_op.drop_constraint(
            'uq_queue_entries_project_order',
            type_='unique',
        )

"""add_action_type_action_params_to_event_rules

Revision ID: eb34150b2a6b
Revises: e0ace512ffb5
Create Date: 2026-06-08 20:01:23.915237

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'eb34150b2a6b'
down_revision: Union[str, None] = 'e0ace512ffb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('pipeline_event_rules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('action_type', sa.String(length=50), nullable=False, server_default='redirect'))
        batch_op.add_column(sa.Column('action_params', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('pipeline_event_rules', schema=None) as batch_op:
        batch_op.drop_column('action_params')
        batch_op.drop_column('action_type')

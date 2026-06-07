"""add pipeline_event_rules table

Revision ID: fa326b3a9bb1
Revises: ea6dc15a673d
Create Date: 2026-06-05 15:10:59.033135

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa326b3a9bb1'
down_revision: Union[str, None] = 'ea6dc15a673d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('pipeline_event_rules',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('pipeline_id', sa.String(length=36), nullable=False),
    sa.Column('event_type', sa.String(length=50), nullable=False),
    sa.Column('source_step_id', sa.String(length=36), nullable=False),
    sa.Column('target_step_id', sa.String(length=36), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_step_id'], ['pipeline_steps.id'], ),
    sa.ForeignKeyConstraint(['target_step_id'], ['pipeline_steps.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('pipeline_id', 'event_type', 'source_step_id', name='uq_pipeline_event_rule')
    )


def downgrade() -> None:
    op.drop_table('pipeline_event_rules')

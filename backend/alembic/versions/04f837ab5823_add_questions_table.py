"""add questions table

Revision ID: 04f837ab5823
Revises: 6fbb705de97e
Create Date: 2026-05-21 11:21:08.463144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '04f837ab5823'
down_revision: Union[str, None] = '6fbb705de97e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('questions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('project_id', sa.String(length=36), nullable=False),
    sa.Column('issue_id', sa.String(length=36), nullable=False),
    sa.Column('question', sa.Text(), nullable=False),
    sa.Column('options', sqlite.JSON(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('answer', sa.Text(), nullable=True),
    sa.Column('selected_option', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('answered_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('questions')

"""add memories, memory_links, and memories_fts

Revision ID: f1a2b3c4d5e6
Revises: e7a9b1c2d3e4
Create Date: 2026-04-21 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e7a9b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'memories',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('parent_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['memories.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_memories_project', 'memories', ['project_id'])
    op.create_index('ix_memories_parent', 'memories', ['parent_id'])

    op.create_table(
        'memory_links',
        sa.Column('from_id', sa.String(length=36), nullable=False),
        sa.Column('to_id', sa.String(length=36), nullable=False),
        sa.Column('relation', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.ForeignKeyConstraint(['from_id'], ['memories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_id'], ['memories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('from_id', 'to_id', 'relation'),
    )
    op.create_index('ix_memory_links_to', 'memory_links', ['to_id'])

    op.execute(
        "CREATE VIRTUAL TABLE memories_fts USING fts5("
        "title, description, "
        "content='memories', content_rowid='rowid', "
        "tokenize='unicode61')"
    )
    op.execute(
        "CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN "
        "INSERT INTO memories_fts(rowid, title, description) "
        "VALUES (new.rowid, new.title, new.description); END;"
    )
    op.execute(
        "CREATE TRIGGER memories_ad AFTER DELETE ON memories BEGIN "
        "INSERT INTO memories_fts(memories_fts, rowid, title, description) "
        "VALUES ('delete', old.rowid, old.title, old.description); END;"
    )
    op.execute(
        "CREATE TRIGGER memories_au AFTER UPDATE ON memories BEGIN "
        "INSERT INTO memories_fts(memories_fts, rowid, title, description) "
        "VALUES ('delete', old.rowid, old.title, old.description); "
        "INSERT INTO memories_fts(rowid, title, description) "
        "VALUES (new.rowid, new.title, new.description); END;"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS memories_au")
    op.execute("DROP TRIGGER IF EXISTS memories_ad")
    op.execute("DROP TRIGGER IF EXISTS memories_ai")
    op.execute("DROP TABLE IF EXISTS memories_fts")
    op.drop_index('ix_memory_links_to', table_name='memory_links')
    op.drop_table('memory_links')
    op.drop_index('ix_memories_parent', table_name='memories')
    op.drop_index('ix_memories_project', table_name='memories')
    op.drop_table('memories')

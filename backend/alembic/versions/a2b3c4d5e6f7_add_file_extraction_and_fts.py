"""add file extraction cache and project_files_fts

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-21 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("project_files") as batch:
        batch.add_column(sa.Column("extracted_text", sa.Text(), nullable=True))
        batch.add_column(sa.Column("extraction_status", sa.String(length=20), nullable=False, server_default="pending"))
        batch.add_column(sa.Column("extraction_error", sa.Text(), nullable=True))
        batch.add_column(sa.Column("extracted_at", sa.DateTime(), nullable=True))

    op.execute(
        "CREATE VIRTUAL TABLE project_files_fts USING fts5("
        "original_name, extracted_text, "
        "content='project_files', content_rowid='rowid', "
        "tokenize='unicode61')"
    )
    op.execute(
        "CREATE TRIGGER project_files_ai AFTER INSERT ON project_files BEGIN "
        "INSERT INTO project_files_fts(rowid, original_name, extracted_text) "
        "VALUES (new.rowid, new.original_name, COALESCE(new.extracted_text, '')); END;"
    )
    op.execute(
        "CREATE TRIGGER project_files_ad AFTER DELETE ON project_files BEGIN "
        "INSERT INTO project_files_fts(project_files_fts, rowid, original_name, extracted_text) "
        "VALUES ('delete', old.rowid, old.original_name, COALESCE(old.extracted_text, '')); END;"
    )
    op.execute(
        "CREATE TRIGGER project_files_au AFTER UPDATE ON project_files BEGIN "
        "INSERT INTO project_files_fts(project_files_fts, rowid, original_name, extracted_text) "
        "VALUES ('delete', old.rowid, old.original_name, COALESCE(old.extracted_text, '')); "
        "INSERT INTO project_files_fts(rowid, original_name, extracted_text) "
        "VALUES (new.rowid, new.original_name, COALESCE(new.extracted_text, '')); END;"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS project_files_au")
    op.execute("DROP TRIGGER IF EXISTS project_files_ad")
    op.execute("DROP TRIGGER IF EXISTS project_files_ai")
    op.execute("DROP TABLE IF EXISTS project_files_fts")
    with op.batch_alter_table("project_files") as batch:
        batch.drop_column("extracted_at")
        batch.drop_column("extraction_error")
        batch.drop_column("extraction_status")
        batch.drop_column("extracted_text")

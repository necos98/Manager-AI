"""prepare_for_file_storage

Revision ID: 57caaadbd338
Revises: 347c2ef09894
Create Date: 2026-04-23 15:55:02.130993

Drops FTS5 virtual tables + triggers (memories_fts, project_files_fts)
and the activity_logs.issue_id FK constraint. Data-carrying tables
(issues, tasks, issue_feedback, issue_relations, memories, memory_links,
project_files) are left intact as backup during the file-storage soak
period; a later revision (B) will drop them.

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '57caaadbd338'
down_revision: Union[str, None] = '347c2ef09894'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Memories FTS
    op.execute("DROP TRIGGER IF EXISTS memories_au")
    op.execute("DROP TRIGGER IF EXISTS memories_ad")
    op.execute("DROP TRIGGER IF EXISTS memories_ai")
    op.execute("DROP TABLE IF EXISTS memories_fts")

    # Project files FTS
    op.execute("DROP TRIGGER IF EXISTS project_files_au")
    op.execute("DROP TRIGGER IF EXISTS project_files_ad")
    op.execute("DROP TRIGGER IF EXISTS project_files_ai")
    op.execute("DROP TABLE IF EXISTS project_files_fts")

    # activity_logs.issue_id FK — SQLite can't drop an unnamed FK in place,
    # so rebuild the table without it. Preserves data, indexes, and the
    # project_id FK.
    op.execute(
        """
        CREATE TABLE activity_logs_new (
            id VARCHAR(36) NOT NULL,
            project_id VARCHAR(36) NOT NULL,
            issue_id VARCHAR(36),
            event_type VARCHAR(64) NOT NULL,
            details TEXT NOT NULL,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "INSERT INTO activity_logs_new (id, project_id, issue_id, event_type, details, created_at) "
        "SELECT id, project_id, issue_id, event_type, details, created_at FROM activity_logs"
    )
    op.execute("DROP TABLE activity_logs")
    op.execute("ALTER TABLE activity_logs_new RENAME TO activity_logs")
    op.execute("CREATE INDEX ix_activity_logs_created_at ON activity_logs (created_at)")
    op.execute("CREATE INDEX ix_activity_logs_issue_id ON activity_logs (issue_id)")
    op.execute("CREATE INDEX ix_activity_logs_project_id ON activity_logs (project_id)")


def downgrade() -> None:
    # Restore activity_logs with issue_id FK via table rebuild.
    op.execute(
        """
        CREATE TABLE activity_logs_new (
            id VARCHAR(36) NOT NULL,
            project_id VARCHAR(36) NOT NULL,
            issue_id VARCHAR(36),
            event_type VARCHAR(64) NOT NULL,
            details TEXT NOT NULL,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(issue_id) REFERENCES issues (id) ON DELETE SET NULL,
            FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "INSERT INTO activity_logs_new (id, project_id, issue_id, event_type, details, created_at) "
        "SELECT id, project_id, issue_id, event_type, details, created_at FROM activity_logs"
    )
    op.execute("DROP TABLE activity_logs")
    op.execute("ALTER TABLE activity_logs_new RENAME TO activity_logs")
    op.execute("CREATE INDEX ix_activity_logs_created_at ON activity_logs (created_at)")
    op.execute("CREATE INDEX ix_activity_logs_issue_id ON activity_logs (issue_id)")
    op.execute("CREATE INDEX ix_activity_logs_project_id ON activity_logs (project_id)")

    # Re-create project_files FTS + triggers
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

    # Re-create memories FTS + triggers
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

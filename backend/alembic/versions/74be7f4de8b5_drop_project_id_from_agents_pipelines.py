"""drop project_id from agents and pipelines

Revision ID: 74be7f4de8b5
Revises: f0b1c2d3e4f5
Create Date: 2026-05-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "74be7f4de8b5"
down_revision: Union[str, None] = "f0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support DROP COLUMN or DROP CONSTRAINT directly.
    # Rebuild each table without the project_id column.

    # ── agents ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE _agents_new (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            system_prompt TEXT NOT NULL,
            model VARCHAR(50),
            allowed_tools JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("INSERT INTO _agents_new SELECT id, name, system_prompt, model, allowed_tools, created_at, updated_at FROM agents")
    op.execute("DROP TABLE agents")
    op.execute("ALTER TABLE _agents_new RENAME TO agents")

    # ── pipelines ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE _pipelines_new (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("INSERT INTO _pipelines_new SELECT id, name, created_at, updated_at FROM pipelines")
    op.execute("DROP TABLE pipelines")
    op.execute("ALTER TABLE _pipelines_new RENAME TO pipelines")


def downgrade() -> None:
    # Re-add project_id columns (nullable — can't recover original values).

    op.execute("""
        CREATE TABLE _agents_old (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            project_id VARCHAR(36),
            name VARCHAR(255) NOT NULL,
            system_prompt TEXT NOT NULL,
            model VARCHAR(50),
            allowed_tools JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)
    op.execute("INSERT INTO _agents_old SELECT id, NULL, name, system_prompt, model, allowed_tools, created_at, updated_at FROM agents")
    op.execute("DROP TABLE agents")
    op.execute("ALTER TABLE _agents_old RENAME TO agents")

    op.execute("""
        CREATE TABLE _pipelines_old (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            project_id VARCHAR(36),
            name VARCHAR(255) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)
    op.execute("INSERT INTO _pipelines_old SELECT id, NULL, name, created_at, updated_at FROM pipelines")
    op.execute("DROP TABLE pipelines")
    op.execute("ALTER TABLE _pipelines_old RENAME TO pipelines")

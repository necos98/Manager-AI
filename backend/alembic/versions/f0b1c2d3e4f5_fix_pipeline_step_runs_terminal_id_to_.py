"""fix pipeline_step_runs terminal_id to string

Revision ID: f0b1c2d3e4f5
Revises: e3b028c8b53a
Create Date: 2026-05-27 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0b1c2d3e4f5'
down_revision: Union[str, None] = 'e3b028c8b53a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Recreate table with terminal_id as String(36) instead of Integer.
    # SQLite can't alter column types or drop FKs directly, so we
    # rebuild the table without the FK to terminal_commands.
    op.execute("""
        CREATE TABLE _pipeline_step_runs_new (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            pipeline_run_id VARCHAR(36) NOT NULL,
            pipeline_step_id VARCHAR(36) NOT NULL,
            terminal_id VARCHAR(36),
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            started_at DATETIME,
            finished_at DATETIME,
            FOREIGN KEY(pipeline_run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE,
            FOREIGN KEY(pipeline_step_id) REFERENCES pipeline_steps(id)
        )
    """)
    op.execute("INSERT INTO _pipeline_step_runs_new SELECT * FROM pipeline_step_runs")
    op.execute("DROP TABLE pipeline_step_runs")
    op.execute("ALTER TABLE _pipeline_step_runs_new RENAME TO pipeline_step_runs")
    op.create_index('ix_pipeline_step_runs_pipeline_run_id', 'pipeline_step_runs', ['pipeline_run_id'])


def downgrade() -> None:
    # Revert: recreate table with terminal_id as Integer with FK.
    op.execute("""
        CREATE TABLE _pipeline_step_runs_old (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            pipeline_run_id VARCHAR(36) NOT NULL,
            pipeline_step_id VARCHAR(36) NOT NULL,
            terminal_id INTEGER,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            started_at DATETIME,
            finished_at DATETIME,
            FOREIGN KEY(pipeline_run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE,
            FOREIGN KEY(pipeline_step_id) REFERENCES pipeline_steps(id),
            FOREIGN KEY(terminal_id) REFERENCES terminal_commands(id) ON DELETE SET NULL
        )
    """)
    op.execute("INSERT INTO _pipeline_step_runs_old SELECT * FROM pipeline_step_runs")
    op.execute("DROP TABLE pipeline_step_runs")
    op.execute("ALTER TABLE _pipeline_step_runs_old RENAME TO pipeline_step_runs")
    op.create_index('ix_pipeline_step_runs_pipeline_run_id', 'pipeline_step_runs', ['pipeline_run_id'])

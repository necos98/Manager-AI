"""add pipeline_logs table

Revision ID: a7b8c9d0e1f2
Revises: b5e9f3d2c4a6
Create Date: 2026-06-07 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "b5e9f3d2c4a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("step_run_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.String(length=10), nullable=False, server_default="INFO"),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(datetime('now'))"), nullable=False),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["step_run_id"],
            ["pipeline_step_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("pipeline_logs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_pipeline_logs_uuid"), ["uuid"], unique=True)
        batch_op.create_index(batch_op.f("ix_pipeline_logs_pipeline_run_id"), ["pipeline_run_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_pipeline_logs_step_run_id"), ["step_run_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_pipeline_logs_created_at"), ["created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("pipeline_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_pipeline_logs_uuid"))
        batch_op.drop_index(batch_op.f("ix_pipeline_logs_pipeline_run_id"))
        batch_op.drop_index(batch_op.f("ix_pipeline_logs_step_run_id"))
        batch_op.drop_index(batch_op.f("ix_pipeline_logs_created_at"))
    op.drop_table("pipeline_logs")

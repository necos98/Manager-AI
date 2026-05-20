"""add agents and pipelines

Revision ID: 6fbb705de97e
Revises: 9a752a193fcf
Create Date: 2026-05-19 15:11:57.008650

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6fbb705de97e'
down_revision: Union[str, None] = '9a752a193fcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role_key", sa.String(100), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "pipelines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("steps", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("trigger_type", sa.String(50), nullable=False, server_default="issue_accepted"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pipeline_id", sa.String(36), sa.ForeignKey("pipelines.id"), nullable=False),
        sa.Column("issue_id", sa.String(36), sa.ForeignKey("issues.id"), nullable=True),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "agent_step_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pipeline_run_id", sa.String(36), sa.ForeignKey("pipeline_runs.id"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("agent_name", sa.String(255), nullable=False),
        sa.Column("agent_role", sa.String(100), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "agent_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("issue_id", sa.String(36), sa.ForeignKey("issues.id"), nullable=False),
        sa.Column("agent_name", sa.String(255), nullable=False),
        sa.Column("agent_role", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False, server_default="context"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("agent_messages")
    op.drop_table("agent_step_runs")
    op.drop_table("pipeline_runs")
    op.drop_table("pipelines")
    op.drop_table("agents")

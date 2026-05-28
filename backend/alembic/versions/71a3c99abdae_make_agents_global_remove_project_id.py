"""make_agents_global_remove_project_id

Revision ID: 71a3c99abdae
Revises: 12d77f379564
Create Date: 2026-05-28 14:44:49.551321

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '71a3c99abdae'
down_revision: Union[str, None] = '12d77f379564'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Deduplicate: for each agent name, keep the oldest and remap pipeline_steps
    dupes = conn.execute(text("""
        SELECT name, COUNT(*) as cnt
        FROM agents
        GROUP BY name
        HAVING cnt > 1
    """)).fetchall()

    for (name, _) in dupes:
        rows = conn.execute(text("""
            SELECT id, project_id, created_at
            FROM agents
            WHERE name = :name
            ORDER BY created_at ASC NULLS LAST
        """), {"name": name}).fetchall()

        keeper_id = rows[0][0]
        for row in rows[1:]:
            dupe_id = row[0]
            conn.execute(text("""
                UPDATE pipeline_steps
                SET agent_id = :keeper_id
                WHERE agent_id = :dupe_id
            """), {"keeper_id": keeper_id, "dupe_id": dupe_id})
            conn.execute(text("DELETE FROM agents WHERE id = :id"), {"id": dupe_id})

    # 2. Rebuild agents table without project_id
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.drop_index('ix_agents_project_id')
        batch_op.drop_constraint('uq_agent_project_name', type_='unique')
        batch_op.drop_column('project_id')

    # 3. Add unique constraint on name only
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_agent_name', ['name'])


def downgrade() -> None:
    # Cannot restore project_id values — this migration is one-way.
    # The unique constraint on name alone is valid for global agents.
    pass

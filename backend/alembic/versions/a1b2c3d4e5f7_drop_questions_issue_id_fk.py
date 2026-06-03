"""drop FK constraint on questions.issue_id — issues are file-backed

Revision ID: a1b2c3d4e5f7
Revises: ff1bd3e20a07
Create Date: 2026-06-03 14:32:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'ff1bd3e20a07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(conn, only=['questions'])
    src = meta.tables['questions']
    # Remove FK referencing issues.id (issues are file-backed, not in DB).
    # FK on project_id must be preserved (projects ARE in DB).
    for fk in list(src.foreign_key_constraints):
        colspecs = [e.target_fullname for e in fk.elements]
        if 'issues.id' in colspecs:
            src.foreign_key_constraints.remove(fk)
    with op.batch_alter_table('questions', copy_from=src, recreate='always') as batch_op:
        pass


def downgrade() -> None:
    with op.batch_alter_table('questions') as batch_op:
        batch_op.create_foreign_key(None, 'issues', ['issue_id'], ['id'])

"""properly_drop_questions_issue_id_fk

Revision ID: ea6dc15a673c
Revises: a1b2c3d4e5f7
Create Date: 2026-06-04 09:57:24.651490

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ea6dc15a673c'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _dialect_name() -> str:
    """Return the dialect name of the bind connection."""
    bind = op.get_bind()
    return bind.dialect.name


def upgrade() -> None:
    dialect = _dialect_name()

    if dialect == 'sqlite':
        # Alembic's batch mode (copy_from + recreate='always') cannot
        # reliably remove FK constraints from SQLite tables because:
        # 1. src.foreign_key_constraints is a memoized copy — removing
        #    from it doesn't remove from src.constraints
        # 2. Even removing from src.constraints is insufficient —
        #    _grab_table_elements copies Column objects with their FK
        #    metadata, and _transfer_elements_to_new_table recreates FKs
        # 3. src.columns['issue_id'].foreign_keys.clear() is also
        #    ineffective because the copy_from Table is internally
        #    re-reflected during batch processing
        #
        # Direct table recreation is the only reliable approach for SQLite.
        conn = op.get_bind()
        conn.exec_driver_sql("PRAGMA foreign_keys = OFF")

        meta = sa.MetaData()
        meta.reflect(conn, only=['questions'])
        src = meta.tables['questions']

        # Build new CREATE TABLE without the issue_id FK
        cols = []
        for c in src.columns:
            col_sql = f"{c.name} {c.type}"
            if c.nullable is False:
                col_sql += " NOT NULL"
            if c.primary_key:
                col_sql += " PRIMARY KEY"
            if c.server_default is not None:
                default_text = str(c.server_default.arg)
                col_sql += f" DEFAULT ({default_text})"
            cols.append(f"\t{col_sql}")

        # Keep project_id FK but NOT issue_id FK
        constraints = []
        for fk in src.constraints:
            if isinstance(fk, sa.ForeignKeyConstraint):
                colspecs = [e.target_fullname for e in fk.elements]
                if 'issues.id' in colspecs:
                    continue  # drop FK to issues
                ref_table = fk.elements[0]._get_colspec().split(".")[0]
                local_cols = [e.parent.name for e in fk.elements]
                constraints.append(
                    f"\tFOREIGN KEY ({', '.join(local_cols)}) "
                    f"REFERENCES {ref_table} (id)"
                )

        create_sql = (
            "CREATE TABLE _questions_new (\n" +
            ",\n".join(cols + constraints) +
            "\n)"
        )

        conn.exec_driver_sql("DROP TABLE IF EXISTS _questions_new")
        conn.exec_driver_sql(create_sql)

        col_list = ", ".join(c.name for c in src.columns)
        conn.exec_driver_sql(
            f"INSERT INTO _questions_new ({col_list}) "
            f"SELECT {col_list} FROM questions"
        )

        conn.exec_driver_sql("DROP TABLE questions")
        conn.exec_driver_sql("ALTER TABLE _questions_new RENAME TO questions")
    else:
        # For non-SQLite dialects, use alembic's batch mode
        with op.batch_alter_table('questions') as batch_op:
            batch_op.drop_constraint('fk_questions_issue_id', type_='foreignkey')


def downgrade() -> None:
    # Previous migration a1b2c3d4e5f7 claimed to drop this FK but didn't.
    # If we ever need the FK back, it must be added as a named constraint
    # via a new migration that also adds the sync step to create Issue DB
    # rows for file-backed issues.
    pass

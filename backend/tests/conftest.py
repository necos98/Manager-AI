import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models import (  # noqa: F401
    ActivityLog, Issue, IssueFeedback, IssueRelation, Memory, MemoryLink,
    Project, ProjectFile, ProjectSkill, PromptTemplate, Setting, Task, TerminalCommand,
)
from app.models.issue_relation import IssueRelation  # noqa: F401
from app.models.project_variable import ProjectVariable  # noqa: F401


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Enable FK enforcement and ignore unknown column types (Vector) in SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create tables, skipping Vector columns that SQLite can't handle
    def _create_tables(connection):
        # Temporarily remove Vector columns before creating tables
        vector_columns = {}
        for table in Base.metadata.tables.values():
            cols_to_remove = []
            for col in table.columns:
                if hasattr(col.type, '__class__') and col.type.__class__.__name__ == 'Vector':
                    cols_to_remove.append(col)
            if cols_to_remove:
                vector_columns[table.name] = cols_to_remove
                for col in cols_to_remove:
                    table._columns.remove(col)

        Base.metadata.create_all(connection)

        # Restore Vector columns
        for table_name, cols in vector_columns.items():
            table = Base.metadata.tables[table_name]
            for col in cols:
                table.append_column(col)

        connection.exec_driver_sql(
            "CREATE VIRTUAL TABLE memories_fts USING fts5("
            "title, description, "
            "content='memories', content_rowid='rowid', "
            "tokenize='unicode61')"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN "
            "INSERT INTO memories_fts(rowid, title, description) "
            "VALUES (new.rowid, new.title, new.description); END;"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER memories_ad AFTER DELETE ON memories BEGIN "
            "INSERT INTO memories_fts(memories_fts, rowid, title, description) "
            "VALUES ('delete', old.rowid, old.title, old.description); END;"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER memories_au AFTER UPDATE ON memories BEGIN "
            "INSERT INTO memories_fts(memories_fts, rowid, title, description) "
            "VALUES ('delete', old.rowid, old.title, old.description); "
            "INSERT INTO memories_fts(rowid, title, description) "
            "VALUES (new.rowid, new.title, new.description); END;"
        )
        connection.exec_driver_sql(
            "CREATE VIRTUAL TABLE project_files_fts USING fts5("
            "original_name, extracted_text, "
            "content='project_files', content_rowid='rowid', "
            "tokenize='unicode61')"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER project_files_ai AFTER INSERT ON project_files BEGIN "
            "INSERT INTO project_files_fts(rowid, original_name, extracted_text) "
            "VALUES (new.rowid, new.original_name, COALESCE(new.extracted_text, '')); END;"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER project_files_ad AFTER DELETE ON project_files BEGIN "
            "INSERT INTO project_files_fts(project_files_fts, rowid, original_name, extracted_text) "
            "VALUES ('delete', old.rowid, old.original_name, COALESCE(old.extracted_text, '')); END;"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER project_files_au AFTER UPDATE ON project_files BEGIN "
            "INSERT INTO project_files_fts(project_files_fts, rowid, original_name, extracted_text) "
            "VALUES ('delete', old.rowid, old.original_name, COALESCE(old.extracted_text, '')); "
            "INSERT INTO project_files_fts(rowid, original_name, extracted_text) "
            "VALUES (new.rowid, new.original_name, COALESCE(new.extracted_text, '')); END;"
        )

    async with engine.begin() as conn:
        await conn.run_sync(_create_tables)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP TRIGGER IF EXISTS memories_ai")
        await conn.exec_driver_sql("DROP TRIGGER IF EXISTS memories_au")
        await conn.exec_driver_sql("DROP TRIGGER IF EXISTS memories_ad")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS memories_fts")
        await conn.exec_driver_sql("DROP TRIGGER IF EXISTS project_files_ai")
        await conn.exec_driver_sql("DROP TRIGGER IF EXISTS project_files_au")
        await conn.exec_driver_sql("DROP TRIGGER IF EXISTS project_files_ad")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS project_files_fts")
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

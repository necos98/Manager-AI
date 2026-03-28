import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models import (  # noqa: F401
    ActivityLog, Issue, IssueFeedback, Project, ProjectSkill,
    PromptTemplate, Setting, Task, TerminalCommand,
)
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

    async with engine.begin() as conn:
        await conn.run_sync(_create_tables)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

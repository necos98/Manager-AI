from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.migration.db_backup import backup_database, rotate_backups


class TestRotateBackups:
    def test_keep_last_n_files(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        for i in range(10):
            (backup_dir / f"manager_ai_{i}.db").write_text("")
        rotate_backups(str(backup_dir), keep=5)
        remaining = sorted(backup_dir.glob("manager_ai_*.db"))
        assert len(remaining) == 5

    def test_noop_when_under_limit(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        for i in range(3):
            (backup_dir / f"manager_ai_{i}.db").write_text("")
        rotate_backups(str(backup_dir), keep=5)
        assert len(list(backup_dir.glob("manager_ai_*.db"))) == 3

    def test_noop_when_dir_missing(self, tmp_path: Path) -> None:
        rotate_backups(str(tmp_path / "nonexistent"), keep=5)

    def test_noop_when_dir_empty(self, tmp_path: Path) -> None:
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        rotate_backups(str(backup_dir), keep=5)


class TestBackupDatabase:
    def test_creates_backup_with_timestamp(self, tmp_path: Path) -> None:
        db_file = tmp_path / "test.db"
        db_file.write_text("data")
        backup_dir = tmp_path / "backups"
        result = backup_database(str(db_file), str(backup_dir))
        assert result is not None
        assert result.exists()
        assert result.read_text() == "data"
        assert "manager_ai_" in result.name
        assert result.suffix == ".db"

    def test_returns_none_when_db_not_found(self, tmp_path: Path) -> None:
        result = backup_database(str(tmp_path / "nonexistent.db"), str(tmp_path / "backups"))
        assert result is None

    def test_rotates_old_backups(self, tmp_path: Path) -> None:
        db_file = tmp_path / "test.db"
        db_file.write_text("data")
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        for i in range(7):
            (backup_dir / f"manager_ai_{i}.db").write_text("")
        result = backup_database(str(db_file), str(backup_dir), keep=3)
        assert result is not None
        remaining = list(backup_dir.glob("manager_ai_*.db"))
        assert len(remaining) == 3

    def test_creates_backup_dir_if_missing(self, tmp_path: Path) -> None:
        db_file = tmp_path / "test.db"
        db_file.write_text("data")
        backup_dir = tmp_path / "backups"
        result = backup_database(str(db_file), str(backup_dir))
        assert result is not None
        assert backup_dir.exists()


class TestMigrationBackupIntegration:
    async def test_backup_called_when_project_needs_migration(self, db_session, project_with_tmp_path):
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from app.migration.db_to_files import migrate_all_projects

        engine = db_session.bind
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        with patch(
            "app.migration.db_backup.backup_database", return_value=Path("/fake/backup.db")
        ) as mock_backup:
            await migrate_all_projects(factory)
            mock_backup.assert_called_once()

    async def test_backup_skipped_when_project_already_migrated(self, db_session, project_with_tmp_path):
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from app.migration.db_to_files import migrate_all_projects
        from app.storage import atomic, paths

        atomic.ensure_dir(paths.manager_ai_root(project_with_tmp_path.path))
        atomic.write_yaml(paths.migration_sentinel(project_with_tmp_path.path), {})

        engine = db_session.bind
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        with patch(
            "app.migration.db_backup.backup_database"
        ) as mock_backup:
            await migrate_all_projects(factory)
            mock_backup.assert_not_called()

    async def test_migration_continues_when_backup_fails(self, db_session, project_with_tmp_path):
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from app.migration.db_to_files import migrate_all_projects

        engine = db_session.bind
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        with patch(
            "app.migration.db_backup.backup_database",
            side_effect=OSError("disk full"),
        ) as mock_backup:
            results = await migrate_all_projects(factory)
            mock_backup.assert_called_once()
            assert len(results) == 1
            assert not results[0].skipped

    async def test_backup_not_called_when_no_projects(self, db_session):
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from app.migration.db_to_files import migrate_all_projects

        engine = db_session.bind
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        with patch(
            "app.migration.db_backup.backup_database"
        ) as mock_backup:
            results = await migrate_all_projects(factory)
            mock_backup.assert_not_called()
            assert results == []

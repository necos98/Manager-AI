# Implementation Plan: Backup SQLite prima della migrazione flat-system

## File map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/migration/db_backup.py` | Create | `backup_database()`, `rotate_backups()` |
| `backend/tests/test_db_backup.py` | Create | Unit + integration tests for backup module |
| `backend/app/migration/db_to_files.py` | Modify | Pre-flight check in `migrate_all_projects()` |

## Task 1: Modulo `db_backup.py`

**Files:**
- Create: `backend/app/migration/db_backup.py`

### Step 1: Implement `rotate_backups`

```python
def rotate_backups(backup_dir: str, keep: int) -> None:
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return
    files = sorted(backup_path.glob("manager_ai_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files[keep:]:
        f.unlink()
```

### Step 2: Implement `backup_database`

```python
def backup_database(db_path: str, backup_dir: str, keep: int = 5) -> Path | None:
    db_file = Path(db_path)
    if not db_file.exists():
        return None
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    dest = backup_path / f"manager_ai_{timestamp}.db"
    shutil.copy2(db_file, dest)
    rotate_backups(str(backup_path), keep)
    return dest
```

### Step 3: Commit
```
git commit -m "feat: add db_backup module for pre-migration SQLite backup"
```

## Task 2: Test `db_backup`

**Files:**
- Create: `backend/tests/test_db_backup.py`

### Step 1: Write tests

```python
import shutil
import tempfile
from pathlib import Path

import pytest

from app.migration.db_backup import backup_database, rotate_backups


class TestRotateBackups:
    def test_keep_last_n_files(self, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        for i in range(10):
            (backup_dir / f"manager_ai_{i}.db").write_text("")
        rotate_backups(str(backup_dir), keep=5)
        remaining = sorted(backup_dir.glob("manager_ai_*.db"))
        assert len(remaining) == 5

    def test_noop_when_under_limit(self, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        for i in range(3):
            (backup_dir / f"manager_ai_{i}.db").write_text("")
        rotate_backups(str(backup_dir), keep=5)
        assert len(list(backup_dir.glob("manager_ai_*.db"))) == 3

    def test_noop_when_dir_missing(self, tmp_path):
        rotate_backups(str(tmp_path / "nonexistent"), keep=5)

    def test_noop_when_dir_empty(self, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        rotate_backups(str(backup_dir), keep=5)


class TestBackupDatabase:
    def test_creates_backup_with_timestamp(self, tmp_path):
        db_file = tmp_path / "test.db"
        db_file.write_text("data")
        backup_dir = tmp_path / "backups"
        result = backup_database(str(db_file), str(backup_dir))
        assert result is not None
        assert result.exists()
        assert result.read_text() == "data"
        assert "manager_ai_" in result.name
        assert result.suffix == ".db"

    def test_returns_none_when_db_not_found(self, tmp_path):
        result = backup_database(str(tmp_path / "nonexistent.db"), str(tmp_path / "backups"))
        assert result is None

    def test_rotates_old_backups(self, tmp_path):
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

    def test_creates_backup_dir_if_missing(self, tmp_path):
        db_file = tmp_path / "test.db"
        db_file.write_text("data")
        backup_dir = tmp_path / "backups"
        result = backup_database(str(db_file), str(backup_dir))
        assert result is not None
        assert backup_dir.exists()
```

### Step 2: Run tests
```
cd backend && python -m pytest tests/test_db_backup.py -v
```
Expected: 8 passed

### Step 3: Commit
```
git commit -m "test: add unit tests for db_backup module"
```

## Task 3: Pre-flight check in `migrate_all_projects`

**Files:**
- Modify: `backend/app/migration/db_to_files.py`

### Step 1: Add helper `_needs_migration`

Extract the skip-check logic into a helper so we can pre-flight without side effects:

```python
def _needs_migration(project: Project) -> bool:
    if not project.path or not os.path.exists(project.path):
        return False
    sentinel = paths.migration_sentinel(project.path)
    if sentinel.exists():
        return False
    if (
        paths.issues_index(project.path).exists()
        or paths.memories_index(project.path).exists()
        or paths.files_index(project.path).exists()
    ):
        return False
    return True
```

### Step 2: Add pre-flight backup in `migrate_all_projects`

```python
async def migrate_all_projects(session_factory):
    from app.migration.db_backup import backup_database
    from app.config import settings

    async with session_factory() as session:
        projects = (await session.execute(select(Project))).scalars().all()

    # Pre-flight: backup DB if any project needs migration
    if any(_needs_migration(p) for p in projects):
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        backup_dir = str(Path(db_path).parent / "backups")
        try:
            backup_path = backup_database(db_path, backup_dir)
            if backup_path:
                logger.info("DB backed up to %s before migration", backup_path)
        except Exception:
            logger.warning("Failed to backup database before migration; continuing anyway", exc_info=True)

    results = []
    async with session_factory() as session:
        for project in projects:
            ...
```

### Step 3: Refactor `migrate_project` to use `_needs_migration`

Replace the inline skip checks at the top of `migrate_project` with a call to `_needs_migration`. If it returns False, determine the specific skip reason for the summary (path_missing, already_migrated, already_populated) — keep the detailed reason logic.

### Step 4: Run existing migration tests
```
cd backend && python -m pytest tests/test_migration_db_to_files.py -v
```
Expected: all existing tests still pass

### Step 5: Commit
```
git commit -m "feat: backup SQLite database before flat-system migration"
```

## Task 4: Integration tests

**Files:**
- Modify: `backend/tests/test_db_backup.py` (or `test_migration_db_to_files.py`)

### Step 1: Write integration tests

Add to `test_db_backup.py`:

```python
class TestMigrationIntegration:
    async def test_migrate_all_projects_backups_when_needed(self, db_session, tmp_path):
        project = Project(id="test", name="Test", path=str(tmp_path), description="", tech_stack="")
        db_session.add(project)
        await db_session.commit()
        # Migration should trigger backup since project is not yet migrated
        from app.migration.db_to_files import migrate_all_projects
        results = await migrate_all_projects(async_session)
        assert len(results) == 1
        assert not results[0].skipped
        # Verify backup was created
        import glob
        backups = list(Path("data/backups").glob("manager_ai_*.db"))
        # At least one backup file created during this test

    async def test_migrate_all_projects_skips_backup_when_all_migrated(self, db_session, tmp_path):
        # Setup project already migrated (sentinel exists)
        project = Project(id="test", name="Test", path=str(tmp_path), description="", tech_stack="")
        db_session.add(project)
        await db_session.commit()
        paths.manager_ai_root(str(tmp_path)).mkdir(parents=True)
        paths.migration_sentinel(str(tmp_path)).write_text("")
        # run migration
        results = await migrate_all_projects(async_session)
        assert results[0].skipped
```

### Step 2: Run integration tests
```
cd backend && python -m pytest tests/test_db_backup.py tests/test_migration_db_to_files.py -v
```
Expected: all tests pass

### Step 3: Commit
```
git commit -m "test: add integration tests for migration backup flow"
```

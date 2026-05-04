"""SQLite database backup before flat-system migration.

Creates timestamped copies of the SQLite database in a backups directory,
with automatic rotation to keep only the most recent N backups.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def rotate_backups(backup_dir: str, keep: int) -> None:
    """Delete oldest backup files, keeping only the most recent `keep`."""
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return
    files = sorted(
        backup_path.glob("manager_ai_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for f in files[keep:]:
        f.unlink()
        logger.debug("Rotated old backup: %s", f)


def backup_database(db_path: str, backup_dir: str, keep: int = 5) -> Path | None:
    """Copy the SQLite database to a timestamped backup file.

    Returns the path of the created backup, or None if the source doesn't exist.
    """
    db_file = Path(db_path)
    if not db_file.exists():
        logger.warning("Database file not found at %s, skipping backup", db_path)
        return None

    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    dest = backup_path / f"manager_ai_{timestamp}.db"
    shutil.copy2(db_file, dest)
    logger.info("Database backed up to %s", dest)

    rotate_backups(str(backup_path), keep)
    return dest

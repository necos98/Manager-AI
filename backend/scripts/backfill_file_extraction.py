"""Backfill extracted_text for project_files created before the extraction cache existed.

Run:
    cd backend
    python -m scripts.backfill_file_extraction
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session
from app.models.project_file import ProjectFile
from app.services import file_reader
from app.services.file_service import BASE_DIR


async def main() -> None:
    processed = 0
    updated = 0
    async with async_session() as session:
        stmt = select(ProjectFile).where(ProjectFile.extraction_status == "pending")
        rows = (await session.execute(stmt)).scalars().all()
        for record in rows:
            processed += 1
            file_path = os.path.join(BASE_DIR, record.project_id, record.stored_name)
            if not os.path.exists(file_path):
                record.extraction_status = "failed"
                record.extraction_error = "File missing on disk"
                record.extracted_at = datetime.now(timezone.utc)
                updated += 1
                continue
            result = file_reader.extract(file_path, record.file_type)
            record.extracted_text = result.text or None
            record.extraction_status = result.status
            record.extraction_error = result.error
            record.extracted_at = datetime.now(timezone.utc)
            meta = dict(record.file_metadata or {})
            if result.status == "ok" and file_reader.file_is_low_text(result.text, record.file_size):
                meta["low_text"] = True
            record.file_metadata = meta or None
            updated += 1
            print(f"[{record.id}] {record.original_name} -> {result.status}")
        await session.commit()
    print(f"Done. processed={processed} updated={updated}")


if __name__ == "__main__":
    asyncio.run(main())

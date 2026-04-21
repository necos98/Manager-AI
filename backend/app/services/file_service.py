from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_file import ProjectFile
from app.services import file_reader

ALLOWED_EXTENSIONS = {
    "txt", "md", "doc", "docx", "pdf", "xls", "xlsx",
    "png", "jpg", "jpeg", "gif", "webp",
}

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

MIME_MAP = {
    "txt": "text/plain",
    "md": "text/markdown",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "project_resources")


def _get_extension(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext.lstrip(".").lower()


class FileService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upload_files(self, project_id: str, files: list[UploadFile]) -> list[ProjectFile]:
        project_dir = os.path.join(BASE_DIR, project_id)
        os.makedirs(project_dir, exist_ok=True)

        results = []
        for file in files:
            ext = _get_extension(file.filename)
            if ext not in ALLOWED_EXTENSIONS:
                raise ValueError(f"File type '.{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

            file_id = str(uuid.uuid4())
            stored_name = f"{file_id}.{ext}"
            file_path = os.path.join(project_dir, stored_name)

            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise ValueError(f"File '{file.filename}' exceeds 5 MB limit")

            with open(file_path, "wb") as f:
                f.write(content)

            mime_type = MIME_MAP.get(ext, "application/octet-stream")

            if ext in IMAGE_EXTENSIONS:
                record = ProjectFile(
                    id=file_id,
                    project_id=project_id,
                    original_name=file.filename,
                    stored_name=stored_name,
                    file_type=ext,
                    file_size=len(content),
                    mime_type=mime_type,
                    file_metadata=None,
                    extracted_text=None,
                    extraction_status="skipped",
                    extraction_error=None,
                    extracted_at=None,
                )
            else:
                result = file_reader.extract(file_path, ext)
                meta: dict[str, Any] = {}
                if result.status == "ok" and file_reader.file_is_low_text(result.text, len(content)):
                    meta["low_text"] = True

                record = ProjectFile(
                    id=file_id,
                    project_id=project_id,
                    original_name=file.filename,
                    stored_name=stored_name,
                    file_type=ext,
                    file_size=len(content),
                    mime_type=mime_type,
                    file_metadata=meta or None,
                    extracted_text=result.text or None,
                    extraction_status=result.status,
                    extraction_error=result.error,
                    extracted_at=datetime.now(timezone.utc) if result.status in ("ok", "failed", "unsupported") else None,
                )

            self.session.add(record)
            results.append(record)

        await self.session.flush()
        return results

    async def reextract(self, project_id: str, file_id: str) -> ProjectFile | None:
        record = await self.get_by_id(project_id, file_id)
        if record is None:
            return None
        file_path = os.path.join(BASE_DIR, project_id, record.stored_name)
        if not os.path.exists(file_path):
            record.extraction_status = "failed"
            record.extraction_error = "File missing on disk"
            record.extracted_at = datetime.now(timezone.utc)
            await self.session.flush()
            return record
        result = file_reader.extract(file_path, record.file_type)
        record.extracted_text = result.text or None
        record.extraction_status = result.status
        record.extraction_error = result.error
        record.extracted_at = datetime.now(timezone.utc)
        meta = dict(record.file_metadata or {})
        if result.status == "ok" and file_reader.file_is_low_text(result.text, record.file_size):
            meta["low_text"] = True
        else:
            meta.pop("low_text", None)
        record.file_metadata = meta or None
        await self.session.flush()
        return record

    async def search(self, project_id: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        sql = text(
            "SELECT f.id AS fid, bm25(project_files_fts) AS rank, "
            "snippet(project_files_fts, 1, '[', ']', '…', 12) AS snippet "
            "FROM project_files_fts pf JOIN project_files f ON f.rowid = pf.rowid "
            "WHERE project_files_fts MATCH :q AND f.project_id = :pid "
            "ORDER BY rank LIMIT :lim"
        )
        rows = (await self.session.execute(sql, {"q": query, "pid": project_id, "lim": limit})).all()
        hits: list[dict[str, Any]] = []
        for row in rows:
            record = await self.get_by_id(project_id, row.fid)
            if record is not None:
                hits.append({"file": record, "snippet": row.snippet or "", "rank": float(row.rank)})
        return hits

    async def list_by_project(self, project_id: str) -> list[ProjectFile]:
        result = await self.session.execute(
            select(ProjectFile)
            .where(ProjectFile.project_id == project_id)
            .order_by(ProjectFile.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, project_id: str, file_id: str) -> ProjectFile | None:
        result = await self.session.execute(
            select(ProjectFile)
            .where(ProjectFile.id == file_id, ProjectFile.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, project_id: str, file_id: str) -> bool:
        record = await self.get_by_id(project_id, file_id)
        if record is None:
            return False

        file_path = os.path.join(BASE_DIR, project_id, record.stored_name)
        if os.path.exists(file_path):
            os.remove(file_path)

        await self.session.delete(record)
        await self.session.flush()
        return True

    def get_file_path(self, project_id: str, stored_name: str) -> str:
        return os.path.join(BASE_DIR, project_id, stored_name)

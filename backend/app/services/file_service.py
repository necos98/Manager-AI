"""File-backed FileService.

Physical files continue to live under `.manager_ai/resources/` (layout
unchanged). Metadata for each uploaded file is stored in
`.manager_ai/files.yaml`, with extracted text cached alongside in
`.manager_ai/files/<id>.txt`. The DB session is kept only to resolve
project.path via ProjectService.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import file_reader
from app.services.project_service import ProjectService
from app.storage import file_store, paths
from app.storage.file_store import FileRecord

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


def _get_extension(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext.lstrip(".").lower()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep="T", timespec="microseconds")


class FileService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _path(self, project_id: str) -> str:
        project = await ProjectService(self.session).get_by_id(project_id)
        return project.path

    async def upload_files(self, project_id: str, files: list[UploadFile]) -> list[FileRecord]:
        project_path = await self._path(project_id)
        resources = paths.resources_dir(project_path)
        os.makedirs(resources, exist_ok=True)

        results: list[FileRecord] = []
        for file in files:
            ext = _get_extension(file.filename)
            if ext not in ALLOWED_EXTENSIONS:
                raise ValueError(
                    f"File type '.{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                )

            file_id = str(uuid.uuid4())
            stored_name = f"{file_id}.{ext}"
            file_path = os.path.join(resources, stored_name)

            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise ValueError(
                    f"File '{file.filename}' exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit"
                )

            with open(file_path, "wb") as f:
                f.write(content)

            mime_type = MIME_MAP.get(ext, "application/octet-stream")

            if ext in IMAGE_EXTENSIONS:
                extract_text: str | None = None
                extract_status = "skipped"
                extract_error: str | None = None
                extract_meta: dict[str, Any] | None = None
                extract_at: str | None = None
            else:
                result = file_reader.extract(file_path, ext)
                meta: dict[str, Any] = {}
                if result.status == "ok" and file_reader.file_is_low_text(result.text, len(content)):
                    meta["low_text"] = True
                extract_text = result.text or None
                extract_status = result.status
                extract_error = result.error
                extract_meta = meta or None
                extract_at = _now_iso() if result.status in ("ok", "failed", "unsupported") else None

            record = FileRecord(
                id=file_id,
                original_name=file.filename,
                stored_name=stored_name,
                file_type=ext,
                file_size=len(content),
                mime_type=mime_type,
                extraction_status=extract_status,
                extraction_error=extract_error,
                extracted_at=extract_at,
                created_at=_now_iso(),
                metadata=extract_meta,
                extracted_text=extract_text,
            )
            file_store.create_file(project_path, record)
            results.append(record)

        return results

    async def reextract(self, project_id: str, file_id: str) -> FileRecord | None:
        project_path = await self._path(project_id)
        record = file_store.load_file(project_path, file_id)
        if record is None:
            return None
        file_path = os.path.join(paths.resources_dir(project_path), record.stored_name)
        if not os.path.exists(file_path):
            record.extraction_status = "failed"
            record.extraction_error = "File missing on disk"
            record.extracted_at = _now_iso()
            record.extracted_text = None
            file_store.update_file(project_path, record)
            return record
        result = file_reader.extract(file_path, record.file_type)
        record.extracted_text = result.text or None
        record.extraction_status = result.status
        record.extraction_error = result.error
        record.extracted_at = _now_iso()
        meta = dict(record.metadata or {})
        if result.status == "ok" and file_reader.file_is_low_text(result.text, record.file_size):
            meta["low_text"] = True
        else:
            meta.pop("low_text", None)
        record.metadata = meta or None
        file_store.update_file(project_path, record)
        return record

    async def search(self, project_id: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Naive in-process scan replacing FTS5 over (original_name, extracted_text)."""
        if not query.strip():
            return []
        project_path = await self._path(project_id)
        term = query.lower()
        hits: list[dict[str, Any]] = []
        for light in file_store.list_files(project_path):
            if light.file_type in IMAGE_EXTENSIONS:
                continue
            text = file_store.read_extracted_text(project_path, light.id)
            name_l = light.original_name.lower()
            text_l = text.lower()
            if term in name_l:
                score = 2.0
                snippet = _snippet(light.original_name, term)
            elif term in text_l:
                score = 1.0
                snippet = _snippet(text, term)
            else:
                continue
            hits.append({"file": light, "snippet": snippet, "rank": score})
        hits.sort(key=lambda h: (-h["rank"], h["file"].created_at))
        return hits[:limit]

    async def list_by_project(self, project_id: str) -> list[FileRecord]:
        project_path = await self._path(project_id)
        records = file_store.list_files(project_path)
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records

    async def get_by_id(self, project_id: str, file_id: str) -> FileRecord | None:
        project_path = await self._path(project_id)
        return file_store.load_file(project_path, file_id)

    async def delete(self, project_id: str, file_id: str) -> bool:
        project_path = await self._path(project_id)
        record = file_store.load_file(project_path, file_id)
        if record is None:
            return False
        resource = os.path.join(paths.resources_dir(project_path), record.stored_name)
        if os.path.exists(resource):
            os.remove(resource)
        file_store.delete_file(project_path, file_id)
        return True

    async def get_file_path(self, project_id: str, stored_name: str) -> str:
        project_path = await self._path(project_id)
        return os.path.join(paths.resources_dir(project_path), stored_name)


def _snippet(text: str, term: str) -> str:
    if not text:
        return ""
    lower = text.lower()
    idx = lower.find(term.lower())
    if idx < 0:
        return text[:80]
    start = max(0, idx - 40)
    end = min(len(text), idx + len(term) + 40)
    s = text[start:end]
    if start > 0:
        s = "…" + s
    if end < len(text):
        s = s + "…"
    return s

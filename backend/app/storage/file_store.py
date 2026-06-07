from __future__ import annotations

from dataclasses import dataclass
from app.utils.datetime import now
from typing import Any

from app.storage import atomic, paths
from app.storage.memory_store_core import memory_store as _core


@dataclass
class FileRecord:
    id: str
    original_name: str
    stored_name: str
    file_type: str
    file_size: int
    mime_type: str
    extraction_status: str
    extraction_error: str | None
    extracted_at: str | None
    created_at: str
    metadata: dict | None = None
    extracted_text: str | None = None  # kept in RAM, persisted to disk via write_extracted_text


# Module-level references — injected at startup by main.py
_write_queue: Any = None


def _now_iso() -> str:
    return (
        now()
        .replace(tzinfo=None)
        .isoformat(sep="T", timespec="microseconds")
    )


def inject_write_queue(queue: Any) -> None:
    global _write_queue
    _write_queue = queue


# ---- index helpers ----


def _to_index_entry(record: FileRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "original_name": record.original_name,
        "stored_name": record.stored_name,
        "file_type": record.file_type,
        "file_size": record.file_size,
        "mime_type": record.mime_type,
        "extraction_status": record.extraction_status,
        "extraction_error": record.extraction_error,
        "extracted_at": record.extracted_at,
        "created_at": record.created_at,
        "metadata": record.metadata,
    }


def _index_to_record(entry: dict[str, Any]) -> FileRecord:
    return FileRecord(
        id=str(entry.get("id", "")),
        original_name=str(entry.get("original_name", "")),
        stored_name=str(entry.get("stored_name", "")),
        file_type=str(entry.get("file_type", "")),
        file_size=int(entry.get("file_size", 0)),
        mime_type=str(entry.get("mime_type", "")),
        extraction_status=str(entry.get("extraction_status", "pending")),
        extraction_error=_opt_str(entry.get("extraction_error")),
        extracted_at=_opt_str(entry.get("extracted_at")),
        created_at=_as_str(entry.get("created_at")),
        metadata=entry.get("metadata") if isinstance(entry.get("metadata"), dict) else None,
        extracted_text=None,
    )


# ---- public CRUD ----


def create_file(project_path: str, record: FileRecord) -> None:
    _core.upsert(project_path, "files", record.id, record, _to_index_entry(record))
    if record.extracted_text is not None:
        write_extracted_text(project_path, record.id, record.extracted_text)
    if _write_queue is not None:
        _write_queue.enqueue(
            project_path, "files", record.id, "upsert",
            _record_to_payload(record), _now_iso(),
        )


def update_file(project_path: str, record: FileRecord) -> None:
    _core.upsert(project_path, "files", record.id, record, _to_index_entry(record))
    if record.extracted_text is not None:
        write_extracted_text(project_path, record.id, record.extracted_text)
    else:
        atomic.remove_if_exists(paths.file_text_cache(project_path, record.id))
        # also clear from RAM
        old = _core.get(project_path, "files", record.id)
        if old is not None:
            old.extracted_text = None
    if _write_queue is not None:
        _write_queue.enqueue(
            project_path, "files", record.id, "upsert",
            _record_to_payload(record), _now_iso(),
        )


def load_file(project_path: str, file_id: str) -> FileRecord | None:
    rec = _core.get(project_path, "files", file_id)
    if rec is not None:
        return rec
    # Fallback: load from disk
    entries = _load_entries_from_disk(project_path)
    for e in entries:
        if e.get("id") == file_id:
            rec = _index_to_record(e)
            rec.extracted_text = read_extracted_text(project_path, file_id) or None
            _core.upsert(project_path, "files", file_id, rec, _to_index_entry(rec))
            return rec
    return None


def list_files(project_path: str) -> list[FileRecord]:
    entries = _core.list_index(project_path, "files")
    if entries:
        return [_index_to_record(e) for e in entries]
    # Fallback: read from disk
    disk_entries = _load_entries_from_disk(project_path)
    # Store index entries only (None records) so load_file hits its disk fallback
    for e in disk_entries:
        _core.upsert(project_path, "files", e.get("id", ""), None, e)
    return [_index_to_record(e) for e in disk_entries]


def delete_file(project_path: str, file_id: str) -> None:
    _core.delete(project_path, "files", file_id)
    atomic.remove_if_exists(paths.file_text_cache(project_path, file_id))
    if _write_queue is not None:
        _write_queue.enqueue(
            project_path, "files", file_id, "delete", None, _now_iso(),
        )


def read_extracted_text(project_path: str, file_id: str) -> str:
    text = atomic.read_text(paths.file_text_cache(project_path, file_id))
    return text


def write_extracted_text(project_path: str, file_id: str, text: str) -> None:
    atomic.write_text(paths.file_text_cache(project_path, file_id), text)
    record = _core.get(project_path, "files", file_id)
    if record is not None:
        record.extracted_text = text
        _core.upsert(project_path, "files", file_id, record, _to_index_entry(record))


def invalidate_file_cache(project_path: str) -> None:
    pass  # RAM-first: no cache to invalidate


# ---- index rebuild (called by BackgroundWriter) ----


def rebuild_files_index(project_path: str) -> int:
    entries = _load_entries_from_disk(project_path)
    _write_files_index(project_path, entries)
    return len(entries)


# ---- disk helpers (called by BackgroundWriter) ----


def _write_file_record(project_path: str, payload: dict[str, Any]) -> None:
    """Write file metadata entry from payload dict. Called by BackgroundWriter."""
    entries = _load_entries_from_disk(project_path)
    entries = _merge_payload_into_entries(entries, payload)
    _write_files_index(project_path, entries)


# ---- internal ----


def _load_entries_from_disk(project_path: str) -> list[dict[str, Any]]:
    data = atomic.read_yaml(paths.files_index(project_path)) or {}
    return list(data.get("files") or [])


def _merge_payload_into_entries(entries: list[dict[str, Any]], payload: dict[str, Any]) -> list[dict[str, Any]]:
    file_id = payload.get("id", "")
    remaining = [e for e in entries if e.get("id") != file_id]
    remaining.append({
        "id": file_id,
        "original_name": payload.get("original_name", ""),
        "stored_name": payload.get("stored_name", ""),
        "file_type": payload.get("file_type", ""),
        "file_size": payload.get("file_size", 0),
        "mime_type": payload.get("mime_type", ""),
        "extraction_status": payload.get("extraction_status", "pending"),
        "extraction_error": payload.get("extraction_error"),
        "extracted_at": payload.get("extracted_at"),
        "created_at": payload.get("created_at", ""),
        "metadata": payload.get("metadata"),
    })
    return remaining


def _write_files_index(project_path: str, entries: list[dict[str, Any]]) -> None:
    entries = sorted(entries, key=lambda e: (_as_str(e.get("created_at")), str(e.get("id", ""))))
    atomic.write_yaml(paths.files_index(project_path), {"schema_version": 1, "files": entries})


def _record_to_payload(record: FileRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "original_name": record.original_name,
        "stored_name": record.stored_name,
        "file_type": record.file_type,
        "file_size": record.file_size,
        "mime_type": record.mime_type,
        "extraction_status": record.extraction_status,
        "extraction_error": record.extraction_error,
        "extracted_at": record.extracted_at,
        "created_at": record.created_at,
        "metadata": record.metadata,
    }


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value)
    return s if s else None


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)

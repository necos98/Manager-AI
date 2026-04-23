from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.storage import atomic, paths


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
    extracted_text: str | None = None


def create_file(project_path: str, record: FileRecord) -> None:
    _persist_text(project_path, record)
    _write_files_index(project_path, _merge_entry(_load_entries(project_path), record))


def update_file(project_path: str, record: FileRecord) -> None:
    _persist_text(project_path, record)
    _write_files_index(project_path, _merge_entry(_load_entries(project_path), record))


def load_file(project_path: str, file_id: str) -> FileRecord | None:
    entry = _find_entry(project_path, file_id)
    if entry is None:
        return None
    rec = _entry_to_record(entry)
    rec.extracted_text = read_extracted_text(project_path, file_id) or None
    return rec


def list_files(project_path: str) -> list[FileRecord]:
    return [_entry_to_record(e) for e in _load_entries(project_path)]


def delete_file(project_path: str, file_id: str) -> None:
    entries = [e for e in _load_entries(project_path) if e.get("id") != file_id]
    atomic.remove_if_exists(paths.file_text_cache(project_path, file_id))
    _write_files_index(project_path, entries)


def read_extracted_text(project_path: str, file_id: str) -> str:
    return atomic.read_text(paths.file_text_cache(project_path, file_id))


def write_extracted_text(project_path: str, file_id: str, text: str) -> None:
    atomic.write_text(paths.file_text_cache(project_path, file_id), text)


def rebuild_files_index(project_path: str) -> None:
    entries = _load_entries(project_path)
    _write_files_index(project_path, entries)


def _load_entries(project_path: str) -> list[dict[str, Any]]:
    data = atomic.read_yaml(paths.files_index(project_path)) or {}
    return list(data.get("files") or [])


def _find_entry(project_path: str, file_id: str) -> dict[str, Any] | None:
    for e in _load_entries(project_path):
        if e.get("id") == file_id:
            return e
    return None


def _merge_entry(entries: list[dict[str, Any]], record: FileRecord) -> list[dict[str, Any]]:
    remaining = [e for e in entries if e.get("id") != record.id]
    remaining.append(_record_to_entry(record))
    return remaining


def _record_to_entry(record: FileRecord) -> dict[str, Any]:
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


def _entry_to_record(entry: dict[str, Any]) -> FileRecord:
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


def _persist_text(project_path: str, record: FileRecord) -> None:
    if record.extracted_text is None:
        atomic.remove_if_exists(paths.file_text_cache(project_path, record.id))
    else:
        write_extracted_text(project_path, record.id, record.extracted_text)


def _write_files_index(project_path: str, entries: list[dict[str, Any]]) -> None:
    entries = sorted(entries, key=lambda e: (_as_str(e.get("created_at")), str(e.get("id", ""))))
    atomic.write_yaml(paths.files_index(project_path), {"schema_version": 1, "files": entries})


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value)
    return s if s else None


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)

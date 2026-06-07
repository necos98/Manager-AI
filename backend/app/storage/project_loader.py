from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# Helpers used by _load_project_into_memory

def _read_optional_md(_atomic, _paths, project_path: str, issue_id: str, field_name: str) -> str | None:
    path = _paths.issue_md(project_path, issue_id, field_name)
    if not path.exists():
        return None
    return _atomic.read_text(path)


def _opt_str_static(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value)
    return s if s else None


def _as_iso(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _task_from_dict(d: dict) -> Any:
    from app.storage.issue_store import TaskRecord
    return TaskRecord(
        id=str(d.get("id", "")),
        name=str(d.get("name", "")),
        status=str(d.get("status", "Pending")),
        order=int(d.get("order", 0)),
        created_at=_as_iso(d.get("created_at")),
        updated_at=_as_iso(d.get("updated_at")),
    )


def _relation_from_dict(d: dict) -> Any:
    from app.storage.issue_store import RelationRecord
    return RelationRecord(
        target_id=str(d.get("target_id", "")),
        type=str(d.get("type", "related")),
        created_at=_as_iso(d.get("created_at")),
    )


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def _parse_fm(text: str) -> dict[str, Any]:
    if not text:
        return {"meta": {}, "body": ""}
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {"meta": {}, "body": text}
    import yaml as _yaml
    meta = _yaml.safe_load(m.group(1)) or {}
    return {"meta": meta, "body": m.group(2)}


def _load_project_into_memory(project_path: str, store: Any) -> None:
    """Load all issues, memories, and file metadata from disk into MemoryStore."""
    import re as _re
    from app.storage import atomic as _atomic, paths as _paths

    # --- memories ---
    mem_dir = _paths.memories_dir(project_path)
    mem_records: dict[str, Any] = {}
    mem_index: list[dict[str, Any]] = []
    if mem_dir.exists():
        for md_file in mem_dir.glob("*.md"):
            try:
                parsed = _parse_fm(_atomic.read_text(md_file))
                meta = parsed["meta"] or {}
                body = parsed["body"]
                mid = str(meta.get("id", md_file.stem))
                from app.storage.memory_store import MemoryRecord, MemoryLinkRecord

                def _opt_str(v: Any) -> str | None:
                    if v is None:
                        return None
                    s = str(v)
                    return s if s else None

                def _as_str(v: Any) -> str:
                    if v is None:
                        return ""
                    return str(v)

                def _link_from_dict(d: dict) -> Any:
                    return MemoryLinkRecord(
                        to_id=str(d.get("to_id", "")),
                        relation=str(d.get("relation", "")),
                        created_at=_as_str(d.get("created_at")),
                    )

                record = MemoryRecord(
                    id=mid,
                    project_id=str(meta.get("project_id", "")),
                    title=str(meta.get("title", "")),
                    parent_id=_opt_str(meta.get("parent_id")),
                    description=body,
                    created_at=_as_str(meta.get("created_at")),
                    updated_at=_as_str(meta.get("updated_at")),
                    links=[_link_from_dict(l) for l in (meta.get("links") or [])],
                )
                mem_records[mid] = record
                mem_index.append({
                    "id": mid,
                    "project_id": str(meta.get("project_id", "")),
                    "title": str(meta.get("title", "")),
                    "parent_id": _opt_str(meta.get("parent_id")),
                    "created_at": _as_str(meta.get("created_at")),
                    "updated_at": _as_str(meta.get("updated_at")),
                    "links": list(meta.get("links") or []),
                })
            except Exception:
                logger.warning("Skipping corrupted memory file: %s", md_file)
    mem_index.sort(key=lambda e: (e["created_at"], e["id"]))
    store.init_project(project_path, "memories", mem_records, mem_index)

    # --- issues ---
    issues_dir = _paths.issues_dir(project_path)
    issue_records: dict[str, Any] = {}
    issue_index: list[dict[str, Any]] = []
    if issues_dir.exists():
        for issue_folder in issues_dir.iterdir():
            if not issue_folder.is_dir():
                continue
            yaml_path = issue_folder / "issue.yaml"
            if not yaml_path.exists():
                continue
            try:
                data = _atomic.read_yaml(yaml_path) or {}
                iid = data.get("id", issue_folder.name)
                description = _atomic.read_text(_paths.issue_md(project_path, iid, "description"))
                specification = _read_optional_md(_atomic, _paths, project_path, iid, "specification")
                plan = _read_optional_md(_atomic, _paths, project_path, iid, "plan")
                recap = _read_optional_md(_atomic, _paths, project_path, iid, "recap")
                from app.storage.issue_store import IssueRecord, TaskRecord, RelationRecord

                record = IssueRecord(
                    id=iid,
                    project_id=data.get("project_id", ""),
                    name=data.get("name"),
                    status=data.get("status", "New"),
                    priority=int(data.get("priority", 3)),
                    description=description,
                    specification=specification,
                    plan=plan,
                    recap=recap,
                    created_at=_as_iso(data.get("created_at")),
                    updated_at=_as_iso(data.get("updated_at")),
                    tasks=[_task_from_dict(t) for t in (data.get("tasks") or [])],
                    relations=[_relation_from_dict(r) for r in (data.get("relations") or [])],
                )
                issue_records[iid] = record
                issue_index.append({
                    "id": iid,
                    "project_id": data.get("project_id", ""),
                    "name": data.get("name"),
                    "status": data.get("status", "New"),
                    "priority": int(data.get("priority", 3)),
                    "created_at": _as_iso(data.get("created_at")),
                    "updated_at": _as_iso(data.get("updated_at")),
                })
            except Exception:
                logger.warning("Skipping corrupted issue: %s", issue_folder)
    issue_index.sort(key=lambda e: (e["created_at"], e["id"]))
    store.init_project(project_path, "issues", issue_records, issue_index)

    # --- files ---
    files_index_path = _paths.files_index(project_path)
    file_records: dict[str, Any] = {}
    file_index: list[dict[str, Any]] = []
    if files_index_path.exists():
        try:
            data = _atomic.read_yaml(files_index_path) or {}
            entries = list(data.get("files") or [])
            from app.storage.file_store import FileRecord

            for e in entries:
                fid = str(e.get("id", ""))
                record = FileRecord(
                    id=fid,
                    original_name=str(e.get("original_name", "")),
                    stored_name=str(e.get("stored_name", "")),
                    file_type=str(e.get("file_type", "")),
                    file_size=int(e.get("file_size", 0)),
                    mime_type=str(e.get("mime_type", "")),
                    extraction_status=str(e.get("extraction_status", "pending")),
                    extraction_error=_opt_str_static(e.get("extraction_error")),
                    extracted_at=_opt_str_static(e.get("extracted_at")),
                    created_at=_as_iso(e.get("created_at")),
                    metadata=e.get("metadata") if isinstance(e.get("metadata"), dict) else None,
                    extracted_text=None,
                )
                file_records[fid] = record
                file_index.append({
                    "id": fid,
                    "original_name": e.get("original_name", ""),
                    "stored_name": e.get("stored_name", ""),
                    "file_type": e.get("file_type", ""),
                    "file_size": int(e.get("file_size", 0)),
                    "mime_type": e.get("mime_type", ""),
                    "extraction_status": e.get("extraction_status", "pending"),
                    "extraction_error": e.get("extraction_error"),
                    "extracted_at": e.get("extracted_at"),
                    "created_at": e.get("created_at", ""),
                    "metadata": e.get("metadata"),
                })
        except Exception:
            logger.warning("Skipping corrupted files index: %s", files_index_path)
    store.init_project(project_path, "files", file_records, file_index)

    logger.info(
        "Loaded project %s: %d memories, %d issues, %d files",
        project_path, len(mem_records), len(issue_records), len(file_records),
    )

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import yaml

from app.storage import atomic, paths
from app.storage.memory_store_core import memory_store as _core


@dataclass
class MemoryLinkRecord:
    to_id: str
    relation: str
    created_at: str


@dataclass
class MemoryRecord:
    id: str
    project_id: str
    title: str
    parent_id: str | None
    description: str
    created_at: str
    updated_at: str
    links: list[MemoryLinkRecord] = field(default_factory=list)


# Module-level references — injected at startup by main.py
_write_queue: Any = None


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        .isoformat(sep="T", timespec="microseconds")
    )


def inject_write_queue(queue: Any) -> None:
    global _write_queue
    _write_queue = queue


# ---- index entry helpers ----


def _to_index_entry(record: MemoryRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "project_id": record.project_id,
        "title": record.title,
        "parent_id": record.parent_id,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "links": [asdict(l) for l in sorted(record.links, key=lambda l: (l.to_id, l.relation))],
    }


def _index_to_record(entry: dict[str, Any]) -> MemoryRecord:
    return MemoryRecord(
        id=str(entry.get("id", "")),
        project_id=str(entry.get("project_id", "")),
        title=str(entry.get("title", "")),
        parent_id=_opt_str(entry.get("parent_id")),
        description="",
        created_at=_as_str(entry.get("created_at")),
        updated_at=_as_str(entry.get("updated_at")),
        links=[_link_from_dict(l) for l in (entry.get("links") or [])],
    )


# ---- public CRUD ----


def create_memory(project_path: str, record: MemoryRecord) -> None:
    _core.upsert(project_path, "memories", record.id, record, _to_index_entry(record))
    if _write_queue is not None:
        _write_queue.enqueue(
            project_path, "memories", record.id, "upsert",
            _record_to_payload(record), _now_iso(),
        )


def update_memory(project_path: str, record: MemoryRecord) -> None:
    _core.upsert(project_path, "memories", record.id, record, _to_index_entry(record))
    if _write_queue is not None:
        _write_queue.enqueue(
            project_path, "memories", record.id, "upsert",
            _record_to_payload(record), _now_iso(),
        )


def load_memory(project_path: str, memory_id: str) -> MemoryRecord | None:
    rec = _core.get(project_path, "memories", memory_id)
    if rec is not None:
        return rec
    # Fallback: load from disk (handles externally-added files)
    path = paths.memory_md(project_path, memory_id)
    if not path.exists():
        return None
    parsed = _parse_frontmatter(atomic.read_text(path))
    meta = parsed["meta"] or {}
    body = parsed["body"]
    record = MemoryRecord(
        id=str(meta.get("id", memory_id)),
        project_id=str(meta.get("project_id", "")),
        title=str(meta.get("title", "")),
        parent_id=_opt_str(meta.get("parent_id")),
        description=body,
        created_at=_as_str(meta.get("created_at")),
        updated_at=_as_str(meta.get("updated_at")),
        links=[_link_from_dict(l) for l in (meta.get("links") or [])],
    )
    _core.upsert(project_path, "memories", memory_id, record, _to_index_entry(record))
    return record


def delete_memory(project_path: str, memory_id: str) -> None:
    rec = _core.get(project_path, "memories", memory_id)
    # Detach children
    affected: set[str] = set()
    for other in _core.list_all(project_path, "memories"):
        if other.parent_id == memory_id:
            other.parent_id = None
            _core.upsert(project_path, "memories", other.id, other, _to_index_entry(other))
            if _write_queue is not None:
                _write_queue.enqueue(
                    project_path, "memories", other.id, "upsert",
                    _record_to_payload(other), _now_iso(),
                )
            affected.add(other.id)
    # Strip inbound links
    for other in _core.list_all(project_path, "memories"):
        new_links = [l for l in other.links if l.to_id != memory_id]
        if len(new_links) != len(other.links):
            other.links = new_links
            _core.upsert(project_path, "memories", other.id, other, _to_index_entry(other))
            if _write_queue is not None:
                _write_queue.enqueue(
                    project_path, "memories", other.id, "upsert",
                    _record_to_payload(other), _now_iso(),
                )
            affected.add(other.id)

    _core.delete(project_path, "memories", memory_id)
    if _write_queue is not None:
        _write_queue.enqueue(
            project_path, "memories", memory_id, "delete", None, _now_iso(),
        )


def list_memories(project_path: str) -> list[MemoryRecord]:
    entries = _core.list_index(project_path, "memories")
    if entries:
        return [_index_to_record(e) for e in entries]
    # Fallback: read from disk index
    data = atomic.read_yaml(paths.memories_index(project_path)) or {}
    disk_entries = data.get("memories") or []
    # Store index entries only (None records) so load_memory hits its disk fallback
    for e in disk_entries:
        _core.upsert(project_path, "memories", e.get("id", ""), None, e)
    return [_index_to_record(e) for e in disk_entries]


def list_memories_full(project_path: str) -> list[MemoryRecord]:
    all_records = _core.list_all(project_path, "memories")
    if all_records:
        return list(all_records)
    # Fallback: load from disk via light index + individual loads
    light = list_memories(project_path)
    out: list[MemoryRecord] = []
    for m in light:
        full = load_memory(project_path, m.id)
        if full is not None:
            out.append(full)
    return out


def add_link(project_path: str, from_id: str, link: MemoryLinkRecord) -> None:
    record = _core.get(project_path, "memories", from_id)
    if record is None:
        raise ValueError(f"Memory {from_id} not found")
    existing = [l for l in record.links if not (l.to_id == link.to_id and l.relation == link.relation)]
    existing.append(link)
    existing.sort(key=lambda l: (l.to_id, l.relation))
    record.links = existing
    _core.upsert(project_path, "memories", from_id, record, _to_index_entry(record))
    if _write_queue is not None:
        _write_queue.enqueue(
            project_path, "memories", from_id, "upsert",
            _record_to_payload(record), _now_iso(),
        )


def remove_link(project_path: str, from_id: str, to_id: str, relation: str) -> bool:
    record = _core.get(project_path, "memories", from_id)
    if record is None:
        return False
    before = len(record.links)
    record.links = [l for l in record.links if not (l.to_id == to_id and l.relation == relation)]
    if len(record.links) == before:
        return False
    _core.upsert(project_path, "memories", from_id, record, _to_index_entry(record))
    if _write_queue is not None:
        _write_queue.enqueue(
            project_path, "memories", from_id, "upsert",
            _record_to_payload(record), _now_iso(),
        )
    return True


def invalidate_memory_cache(project_path: str) -> None:
    pass  # RAM-first: no cache to invalidate


# ---- index rebuild (called by BackgroundWriter) ----


def rebuild_memories_index(project_path: str) -> int:
    mem_dir = paths.memories_dir(project_path)
    entries: list[dict[str, Any]] = []
    if mem_dir.exists():
        for md_file in mem_dir.glob("*.md"):
            parsed = _parse_frontmatter(atomic.read_text(md_file))
            meta = parsed["meta"] or {}
            entries.append(
                {
                    "id": str(meta.get("id", md_file.stem)),
                    "project_id": str(meta.get("project_id", "")),
                    "title": str(meta.get("title", "")),
                    "parent_id": _opt_str(meta.get("parent_id")),
                    "created_at": _as_str(meta.get("created_at")),
                    "updated_at": _as_str(meta.get("updated_at")),
                    "links": list(meta.get("links") or []),
                }
            )
    entries.sort(key=lambda e: (e["created_at"], e["id"]))
    atomic.write_yaml(paths.memories_index(project_path), {"schema_version": 1, "memories": entries})
    return len(entries)


# ---- disk write (called by BackgroundWriter) ----


def _write_memory_record(project_path: str, payload: dict[str, Any]) -> None:
    """Write a single .md file from a payload dict. Called by BackgroundWriter."""
    frontmatter: dict[str, Any] = {
        "id": payload.get("id", ""),
        "project_id": payload.get("project_id", ""),
        "title": payload.get("title", ""),
        "parent_id": payload.get("parent_id"),
        "created_at": payload.get("created_at", ""),
        "updated_at": payload.get("updated_at", ""),
        "links": payload.get("links", []),
    }
    fm_yaml = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True, width=4096).rstrip("\n")
    content = f"---\n{fm_yaml}\n---\n{payload.get('description', '')}"
    atomic.write_text(paths.memory_md(project_path, payload.get("id", "")), content)


# ---- helpers ----


def _record_to_payload(record: MemoryRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "project_id": record.project_id,
        "title": record.title,
        "parent_id": record.parent_id,
        "description": record.description,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "links": [asdict(l) for l in sorted(record.links, key=lambda l: (l.to_id, l.relation))],
    }


def _parse_frontmatter(text: str) -> dict[str, Any]:
    import re

    _FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
    if not text:
        return {"meta": {}, "body": ""}
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {"meta": {}, "body": text}
    meta = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return {"meta": meta, "body": body}


def _link_from_dict(d: dict) -> MemoryLinkRecord:
    return MemoryLinkRecord(
        to_id=str(d.get("to_id", "")),
        relation=str(d.get("relation", "")),
        created_at=_as_str(d.get("created_at")),
    )


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value)
    return s if s else None


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)

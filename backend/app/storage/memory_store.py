from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import yaml

from app.storage import atomic, paths
from app.storage.issue_store import _parse_frontmatter


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


def create_memory(project_path: str, record: MemoryRecord) -> None:
    _write_memory_file(project_path, record)
    rebuild_memories_index(project_path)


def update_memory(project_path: str, record: MemoryRecord) -> None:
    _write_memory_file(project_path, record)
    rebuild_memories_index(project_path)


def load_memory(project_path: str, memory_id: str) -> MemoryRecord | None:
    path = paths.memory_md(project_path, memory_id)
    if not path.exists():
        return None
    parsed = _parse_frontmatter(atomic.read_text(path))
    meta = parsed["meta"] or {}
    body = parsed["body"]
    return MemoryRecord(
        id=str(meta.get("id", memory_id)),
        project_id=str(meta.get("project_id", "")),
        title=str(meta.get("title", "")),
        parent_id=_opt_str(meta.get("parent_id")),
        description=body,
        created_at=_as_str(meta.get("created_at")),
        updated_at=_as_str(meta.get("updated_at")),
        links=[_link_from_dict(l) for l in (meta.get("links") or [])],
    )


def delete_memory(project_path: str, memory_id: str) -> None:
    # Detach children
    for other in list_memories_full(project_path):
        if other.parent_id == memory_id:
            other.parent_id = None
            _write_memory_file(project_path, other)
    # Strip inbound links
    for other in list_memories_full(project_path):
        new_links = [l for l in other.links if l.to_id != memory_id]
        if new_links != other.links:
            other.links = new_links
            _write_memory_file(project_path, other)
    atomic.remove_if_exists(paths.memory_md(project_path, memory_id))
    rebuild_memories_index(project_path)


def list_memories(project_path: str) -> list[MemoryRecord]:
    data = atomic.read_yaml(paths.memories_index(project_path)) or {}
    entries = data.get("memories") or []
    return [
        MemoryRecord(
            id=str(e.get("id", "")),
            project_id=str(e.get("project_id", "")),
            title=str(e.get("title", "")),
            parent_id=_opt_str(e.get("parent_id")),
            description="",
            created_at=_as_str(e.get("created_at")),
            updated_at=_as_str(e.get("updated_at")),
            links=[_link_from_dict(l) for l in (e.get("links") or [])],
        )
        for e in entries
    ]


def list_memories_full(project_path: str) -> list[MemoryRecord]:
    light = list_memories(project_path)
    out: list[MemoryRecord] = []
    for m in light:
        full = load_memory(project_path, m.id)
        if full is not None:
            out.append(full)
    return out


def add_link(project_path: str, from_id: str, link: MemoryLinkRecord) -> None:
    record = load_memory(project_path, from_id)
    if record is None:
        raise ValueError(f"Memory {from_id} not found")
    existing = [l for l in record.links if not (l.to_id == link.to_id and l.relation == link.relation)]
    existing.append(link)
    existing.sort(key=lambda l: (l.to_id, l.relation))
    record.links = existing
    _write_memory_file(project_path, record)
    rebuild_memories_index(project_path)


def remove_link(project_path: str, from_id: str, to_id: str, relation: str) -> bool:
    record = load_memory(project_path, from_id)
    if record is None:
        return False
    before = len(record.links)
    record.links = [l for l in record.links if not (l.to_id == to_id and l.relation == relation)]
    if len(record.links) == before:
        return False
    _write_memory_file(project_path, record)
    rebuild_memories_index(project_path)
    return True


def rebuild_memories_index(project_path: str) -> None:
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


def _write_memory_file(project_path: str, record: MemoryRecord) -> None:
    frontmatter: dict[str, Any] = {
        "id": record.id,
        "project_id": record.project_id,
        "title": record.title,
        "parent_id": record.parent_id,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "links": [asdict(l) for l in sorted(record.links, key=lambda l: (l.to_id, l.relation))],
    }
    fm_yaml = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True, width=4096).rstrip("\n")
    content = f"---\n{fm_yaml}\n---\n{record.description or ''}"
    atomic.write_text(paths.memory_md(project_path, record.id), content)


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

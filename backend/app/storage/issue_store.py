from __future__ import annotations

import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.storage import atomic, paths
from app.storage.memory_store_core import memory_store as _core


@dataclass
class TaskRecord:
    id: str
    name: str
    status: str
    order: int
    created_at: str
    updated_at: str


@dataclass
class RelationRecord:
    target_id: str
    type: str
    created_at: str


@dataclass
class FeedbackRecord:
    id: str
    issue_id: str
    content: str
    created_at: str


@dataclass
class IssueRecord:
    id: str
    project_id: str
    name: str | None
    status: str
    priority: int
    category: str | None = None
    description: str
    specification: str | None
    plan: str | None
    recap: str | None
    created_at: str
    updated_at: str
    tasks: list[TaskRecord] = field(default_factory=list)
    relations: list[RelationRecord] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
_MD_FIELDS = ("specification", "plan", "recap")

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


# ---- index helpers ----


def _to_index_entry(record: IssueRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "project_id": record.project_id,
        "name": record.name,
        "status": record.status,
        "priority": record.priority,
        "category": record.category,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _index_to_light_record(entry: dict[str, Any]) -> IssueRecord:
    return IssueRecord(
        id=entry.get("id", ""),
        project_id=entry.get("project_id", ""),
        name=entry.get("name"),
        status=entry.get("status", "New"),
        priority=int(entry.get("priority", 3)),
        category=entry.get("category"),
        description="",
        specification=None,
        plan=None,
        recap=None,
        created_at=_as_iso(entry.get("created_at")),
        updated_at=_as_iso(entry.get("updated_at")),
    )


# ---- public CRUD ----


def issue_exists(project_path: str, issue_id: str) -> bool:
    if _core.get(project_path, "issues", issue_id) is not None:
        return True
    return paths.issue_yaml(project_path, issue_id).exists()


def load_issue(project_path: str, issue_id: str) -> IssueRecord | None:
    rec = _core.get(project_path, "issues", issue_id)
    if rec is not None:
        return rec
    # Fallback: load from disk (handles externally-added files or tests)
    yaml_path = paths.issue_yaml(project_path, issue_id)
    if not yaml_path.exists():
        return None
    data = atomic.read_yaml(yaml_path) or {}
    description = atomic.read_text(paths.issue_md(project_path, issue_id, "description"))
    specification = _read_optional_md(project_path, issue_id, "specification")
    plan = _read_optional_md(project_path, issue_id, "plan")
    recap = _read_optional_md(project_path, issue_id, "recap")
    record = IssueRecord(
        id=data.get("id", issue_id),
        project_id=data.get("project_id", ""),
        name=data.get("name"),
        status=data.get("status", "New"),
        priority=int(data.get("priority", 3)),
        category=data.get("category"),
        description=description,
        specification=specification,
        plan=plan,
        recap=recap,
        tags=data.get("tags") or [],
        created_at=_as_iso(data.get("created_at")),
        updated_at=_as_iso(data.get("updated_at")),
        tasks=[_task_from_dict(t) for t in (data.get("tasks") or [])],
        relations=[_relation_from_dict(r) for r in (data.get("relations") or [])],
    )
    _core.upsert(project_path, "issues", issue_id, record, _to_index_entry(record))
    return record


def list_issues(project_path: str) -> list[IssueRecord]:
    entries = _core.list_index(project_path, "issues")
    if entries:
        return [_index_to_light_record(e) for e in entries]
    # Fallback: read from disk index (handles projects not yet loaded into RAM)
    data = atomic.read_yaml(paths.issues_index(project_path)) or {}
    disk_entries = data.get("issues") or []
    # Store index entries only (None records) so load_issue hits its disk fallback
    for e in disk_entries:
        _core.upsert(project_path, "issues", e.get("id", ""), None, e)
    return [_index_to_light_record(e) for e in disk_entries]


def list_issues_full(project_path: str) -> list[IssueRecord]:
    all_records = _core.list_all(project_path, "issues")
    if all_records:
        return list(all_records)
    # Fallback: load from disk via light index + individual loads
    light = list_issues(project_path)
    out: list[IssueRecord] = []
    for m in light:
        full = load_issue(project_path, m.id)
        if full is not None:
            out.append(full)
    return out


def prewarm_project_cache(project_path: str) -> None:
    pass  # RAM-first: all records loaded at startup


def create_issue(project_path: str, record: IssueRecord) -> None:
    _core.upsert(project_path, "issues", record.id, record, _to_index_entry(record))
    if _write_queue is not None:
        _write_queue.enqueue(
            project_path, "issues", record.id, "upsert",
            _record_to_payload(record), _now_iso(),
        )


def update_issue(project_path: str, record: IssueRecord) -> None:
    _core.upsert(project_path, "issues", record.id, record, _to_index_entry(record))
    if _write_queue is not None:
        _write_queue.enqueue(
            project_path, "issues", record.id, "upsert",
            _record_to_payload(record), _now_iso(),
        )


def delete_issue(project_path: str, issue_id: str) -> None:
    _core.delete(project_path, "issues", issue_id)
    if _write_queue is not None:
        _write_queue.enqueue(
            project_path, "issues", issue_id, "delete", None, _now_iso(),
        )


def upsert_task(project_path: str, issue_id: str, task: TaskRecord) -> None:
    record = _core.get(project_path, "issues", issue_id)
    if record is None:
        raise ValueError(f"Issue {issue_id} not found")
    tasks = [t for t in record.tasks if t.id != task.id]
    tasks.append(task)
    tasks.sort(key=lambda t: (t.order, t.id))
    record.tasks = tasks
    update_issue(project_path, record)


def remove_task(project_path: str, issue_id: str, task_id: str) -> None:
    record = _core.get(project_path, "issues", issue_id)
    if record is None:
        return
    record.tasks = [t for t in record.tasks if t.id != task_id]
    update_issue(project_path, record)


def replace_tasks(project_path: str, issue_id: str, tasks: list[TaskRecord]) -> None:
    record = _core.get(project_path, "issues", issue_id)
    if record is None:
        raise ValueError(f"Issue {issue_id} not found")
    ordered = sorted(tasks, key=lambda t: (t.order, t.id))
    record.tasks = ordered
    update_issue(project_path, record)


def find_task(project_path: str, task_id: str) -> tuple[IssueRecord, TaskRecord] | None:
    for issue in _core.list_all(project_path, "issues"):
        for t in issue.tasks:
            if t.id == task_id:
                return issue, t
    return None


def add_feedback(project_path: str, issue_id: str, feedback: FeedbackRecord) -> None:
    fb_path = paths.issue_feedback_md(project_path, issue_id, feedback.id)
    content = (
        "---\n"
        f"id: {feedback.id}\n"
        f"issue_id: {feedback.issue_id}\n"
        f"created_at: \"{feedback.created_at}\"\n"
        "---\n"
        f"{feedback.content}"
    )
    atomic.write_text(fb_path, content)


def load_feedback(project_path: str, issue_id: str) -> list[FeedbackRecord]:
    fb_dir = paths.issue_feedback_dir(project_path, issue_id)
    if not fb_dir.exists():
        return []
    records: list[FeedbackRecord] = []
    for fb_file in fb_dir.glob("*.md"):
        parsed = _parse_frontmatter(atomic.read_text(fb_file))
        meta = parsed["meta"]
        body = parsed["body"]
        records.append(
            FeedbackRecord(
                id=str(meta.get("id", fb_file.stem)),
                issue_id=str(meta.get("issue_id", issue_id)),
                content=body,
                created_at=_as_iso(meta.get("created_at")),
            )
        )
    records.sort(key=lambda r: (r.created_at, r.id))
    return records


def upsert_relation(project_path: str, issue_id: str, rel: RelationRecord) -> None:
    record = _core.get(project_path, "issues", issue_id)
    if record is None:
        raise ValueError(f"Issue {issue_id} not found")
    existing = [r for r in record.relations if not (r.target_id == rel.target_id and r.type == rel.type)]
    existing.append(rel)
    existing.sort(key=lambda r: (r.type, r.target_id))
    record.relations = existing
    update_issue(project_path, record)


def remove_relation(project_path: str, source_id: str, target_id: str, type: str) -> None:
    record = _core.get(project_path, "issues", source_id)
    if record is None:
        return
    record.relations = [r for r in record.relations if not (r.target_id == target_id and r.type == type)]
    update_issue(project_path, record)


def invalidate_issue_cache(project_path: str) -> None:
    pass  # RAM-first: no cache to invalidate


# ---- index rebuild (called by BackgroundWriter) ----


def rebuild_issues_index(project_path: str) -> int:
    issues_dir = paths.issues_dir(project_path)
    entries: list[dict[str, Any]] = []
    if issues_dir.exists():
        for issue_folder in issues_dir.iterdir():
            if not issue_folder.is_dir():
                continue
            yaml_path = issue_folder / "issue.yaml"
            if not yaml_path.exists():
                continue
            data = atomic.read_yaml(yaml_path) or {}
            entries.append(
                {
                    "id": data.get("id", issue_folder.name),
                    "project_id": data.get("project_id", ""),
                    "name": data.get("name"),
                    "status": data.get("status", "New"),
                    "priority": int(data.get("priority", 3)),
                    "category": data.get("category"),
                    "created_at": _as_iso(data.get("created_at")),
                    "updated_at": _as_iso(data.get("updated_at")),
                }
            )
    entries.sort(key=lambda e: (e["created_at"], e["id"]))
    atomic.write_yaml(paths.issues_index(project_path), {"schema_version": 1, "issues": entries})
    return len(entries)


# ---- disk write (called by BackgroundWriter) ----


def _write_issue_record(project_path: str, payload: dict[str, Any]) -> None:
    """Write issue.yaml + markdown files from a payload dict. Called by BackgroundWriter."""
    issue_id = payload.get("id", "")
    yaml_path = paths.issue_yaml(project_path, issue_id)
    yaml_payload: dict[str, Any] = {
        "schema_version": 1,
        "id": issue_id,
        "project_id": payload.get("project_id", ""),
        "name": payload.get("name"),
        "status": payload.get("status", "New"),
        "priority": int(payload.get("priority", 3)),
        "category": payload.get("category"),
        "created_at": payload.get("created_at", ""),
        "updated_at": payload.get("updated_at", ""),
        "tasks": payload.get("tasks", []),
        "relations": payload.get("relations", []),
    }
    atomic.write_yaml(yaml_path, yaml_payload)
    atomic.write_text(paths.issue_md(project_path, issue_id, "description"), payload.get("description") or "")
    for field_name in _MD_FIELDS:
        value = payload.get(field_name)
        md_path = paths.issue_md(project_path, issue_id, field_name)  # type: ignore[arg-type]
        if value is None:
            atomic.remove_if_exists(md_path)
        else:
            atomic.write_text(md_path, value)


# ---- helpers ----


def _record_to_payload(record: IssueRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "project_id": record.project_id,
        "name": record.name,
        "status": record.status,
        "priority": record.priority,
        "category": record.category,
        "description": record.description,
        "specification": record.specification,
        "plan": record.plan,
        "recap": record.recap,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "tasks": [asdict(t) for t in sorted(record.tasks, key=lambda t: (t.order, t.id))],
        "relations": [asdict(r) for r in sorted(record.relations, key=lambda r: (r.type, r.target_id))],
        "tags": record.tags,
    }


def _read_optional_md(project_path: str, issue_id: str, field_name: str) -> str | None:
    path = paths.issue_md(project_path, issue_id, field_name)  # type: ignore[arg-type]
    if not path.exists():
        return None
    return atomic.read_text(path)


def _task_from_dict(d: dict) -> TaskRecord:
    return TaskRecord(
        id=str(d.get("id", "")),
        name=str(d.get("name", "")),
        status=str(d.get("status", "Pending")),
        order=int(d.get("order", 0)),
        created_at=_as_iso(d.get("created_at")),
        updated_at=_as_iso(d.get("updated_at")),
    )


def _relation_from_dict(d: dict) -> RelationRecord:
    return RelationRecord(
        target_id=str(d.get("target_id", "")),
        type=str(d.get("type", "related")),
        created_at=_as_iso(d.get("created_at")),
    )


def _parse_frontmatter(text: str) -> dict[str, Any]:
    if not text:
        return {"meta": {}, "body": ""}
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {"meta": {}, "body": text}
    import yaml as _yaml

    meta = _yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return {"meta": meta, "body": body}


def _as_iso(value: Any) -> str:
    if value is None:
        return ""
    return str(value)

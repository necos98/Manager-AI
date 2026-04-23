from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.storage import atomic, paths


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
    description: str
    specification: str | None
    plan: str | None
    recap: str | None
    created_at: str
    updated_at: str
    tasks: list[TaskRecord] = field(default_factory=list)
    relations: list[RelationRecord] = field(default_factory=list)


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def issue_exists(project_path: str, issue_id: str) -> bool:
    return paths.issue_yaml(project_path, issue_id).exists()


def load_issue(project_path: str, issue_id: str) -> IssueRecord | None:
    yaml_path = paths.issue_yaml(project_path, issue_id)
    if not yaml_path.exists():
        return None
    data = atomic.read_yaml(yaml_path) or {}
    description = atomic.read_text(paths.issue_md(project_path, issue_id, "description"))
    specification = _read_optional_md(project_path, issue_id, "specification")
    plan = _read_optional_md(project_path, issue_id, "plan")
    recap = _read_optional_md(project_path, issue_id, "recap")
    return IssueRecord(
        id=data.get("id", issue_id),
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


def list_issues(project_path: str) -> list[IssueRecord]:
    """Light listing from issues.yaml index — no markdown bodies loaded."""
    data = atomic.read_yaml(paths.issues_index(project_path)) or {}
    entries = data.get("issues") or []
    out: list[IssueRecord] = []
    for entry in entries:
        out.append(
            IssueRecord(
                id=entry.get("id", ""),
                project_id=entry.get("project_id", ""),
                name=entry.get("name"),
                status=entry.get("status", "New"),
                priority=int(entry.get("priority", 3)),
                description="",
                specification=None,
                plan=None,
                recap=None,
                created_at=_as_iso(entry.get("created_at")),
                updated_at=_as_iso(entry.get("updated_at")),
            )
        )
    return out


def list_issues_full(project_path: str) -> list[IssueRecord]:
    """Full listing: loads every issue.yaml + all markdown bodies."""
    index = list_issues(project_path)
    out: list[IssueRecord] = []
    for light in index:
        full = load_issue(project_path, light.id)
        if full is not None:
            out.append(full)
    return out


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

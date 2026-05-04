"""One-shot startup migration: dump DB rows into .manager_ai/ per project.

Idempotent via .migration_done sentinel. Non-destructive: DB rows are
left untouched after export. If .manager_ai/ is already populated
(e.g. fresh git clone with committed layout), skip without re-dumping.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog  # noqa: F401 — ensure model loads
from app.models.issue import Issue
from app.models.issue_feedback import IssueFeedback
from app.models.issue_relation import IssueRelation, RelationType
from app.models.memory import Memory, MemoryLink
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.task import Task
from app.storage import atomic, file_store, issue_store, memory_store, paths
from app.storage.file_store import FileRecord
from app.storage.issue_store import (
    FeedbackRecord,
    IssueRecord,
    RelationRecord,
    TaskRecord,
)
from app.storage.memory_store import MemoryLinkRecord, MemoryRecord

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


@dataclass
class MigrationSummary:
    project_id: str
    skipped: bool
    skip_reason: str | None = None
    issues: int = 0
    memories: int = 0
    files: int = 0


async def migrate_all_projects(session_factory: Callable[[], AsyncSession]) -> list[MigrationSummary]:
    results: list[MigrationSummary] = []
    async with session_factory() as session:
        projects = (await session.execute(select(Project))).scalars().all()
        for project in projects:
            try:
                summary = await migrate_project(session, project)
            except Exception:
                logger.exception("Migration failed for project %s (%s)", project.id, project.name)
                summary = MigrationSummary(project_id=project.id, skipped=True, skip_reason="error")
            results.append(summary)
    return results


async def migrate_project(session: AsyncSession, project: Project) -> MigrationSummary:
    summary = MigrationSummary(project_id=project.id, skipped=False)
    if not project.path or not os.path.exists(project.path):
        logger.warning("Project %s path not accessible: %r — skipping migration", project.id, project.path)
        summary.skipped = True
        summary.skip_reason = "path_missing"
        return summary

    sentinel = paths.migration_sentinel(project.path)
    if sentinel.exists():
        summary.skipped = True
        summary.skip_reason = "already_migrated"
        return summary

    # Fresh clone case: file layout already present but no sentinel → just seal it
    if (
        paths.issues_index(project.path).exists()
        or paths.memories_index(project.path).exists()
        or paths.files_index(project.path).exists()
    ):
        _seal_sentinel(project.path, summary)
        summary.skipped = True
        summary.skip_reason = "already_populated"
        return summary

    # Ensure directories
    atomic.ensure_dir(paths.manager_ai_root(project.path))
    atomic.ensure_dir(paths.issues_dir(project.path))
    atomic.ensure_dir(paths.memories_dir(project.path))
    atomic.ensure_dir(paths.files_dir(project.path))
    atomic.ensure_dir(paths.resources_dir(project.path))

    await _dump_issues(session, project, summary)
    await _dump_memories(session, project, summary)
    await _dump_files(session, project, summary)

    _write_gitignore(project.path)
    _seal_sentinel(project.path, summary)

    logger.info(
        "Migrated project %s (%s): %d issues, %d memories, %d files",
        project.id,
        project.name,
        summary.issues,
        summary.memories,
        summary.files,
    )
    return summary


async def _dump_issues(session: AsyncSession, project: Project, summary: MigrationSummary) -> None:
    issues = (await session.execute(select(Issue).where(Issue.project_id == project.id))).scalars().all()
    for issue in issues:
        tasks = (
            await session.execute(select(Task).where(Task.issue_id == issue.id).order_by(Task.order.asc()))
        ).scalars().all()
        feedback = (
            await session.execute(
                select(IssueFeedback).where(IssueFeedback.issue_id == issue.id).order_by(IssueFeedback.created_at.asc())
            )
        ).scalars().all()
        relations = (
            await session.execute(select(IssueRelation).where(IssueRelation.source_id == issue.id))
        ).scalars().all()

        record = IssueRecord(
            id=issue.id,
            project_id=issue.project_id,
            name=issue.name,
            status=issue.status.value if issue.status is not None else "New",
            priority=issue.priority,
            description=issue.description or "",
            specification=issue.specification,
            plan=issue.plan,
            recap=issue.recap,
            created_at=_iso(issue.created_at),
            updated_at=_iso(issue.updated_at),
            tasks=[
                TaskRecord(
                    id=t.id,
                    name=t.name,
                    status=t.status.value if t.status is not None else "Pending",
                    order=t.order,
                    created_at=_iso(t.created_at),
                    updated_at=_iso(t.updated_at),
                )
                for t in tasks
            ],
            relations=[
                RelationRecord(
                    target_id=r.target_id,
                    type=r.relation_type.value if r.relation_type is not None else RelationType.RELATED.value,
                    created_at=_iso(r.created_at),
                )
                for r in relations
            ],
        )
        issue_store.create_issue(project.path, record)

        for fb in feedback:
            issue_store.add_feedback(
                project.path,
                issue.id,
                FeedbackRecord(
                    id=fb.id,
                    issue_id=fb.issue_id,
                    content=fb.content or "",
                    created_at=_iso(fb.created_at),
                ),
            )

        summary.issues += 1


async def _dump_memories(session: AsyncSession, project: Project, summary: MigrationSummary) -> None:
    memories = (await session.execute(select(Memory).where(Memory.project_id == project.id))).scalars().all()
    memory_ids = {m.id for m in memories}
    links = (
        await session.execute(select(MemoryLink).where(MemoryLink.from_id.in_(memory_ids or [""])))
    ).scalars().all()
    links_by_source: dict[str, list[MemoryLinkRecord]] = {}
    for l in links:
        links_by_source.setdefault(l.from_id, []).append(
            MemoryLinkRecord(to_id=l.to_id, relation=l.relation or "", created_at=_iso(l.created_at))
        )

    for m in memories:
        record = MemoryRecord(
            id=m.id,
            project_id=m.project_id,
            title=m.title,
            parent_id=m.parent_id,
            description=m.description or "",
            created_at=_iso(m.created_at),
            updated_at=_iso(m.updated_at),
            links=links_by_source.get(m.id, []),
        )
        memory_store.create_memory(project.path, record)
        summary.memories += 1


async def _dump_files(session: AsyncSession, project: Project, summary: MigrationSummary) -> None:
    files = (
        await session.execute(select(ProjectFile).where(ProjectFile.project_id == project.id))
    ).scalars().all()
    for f in files:
        record = FileRecord(
            id=f.id,
            original_name=f.original_name,
            stored_name=f.stored_name,
            file_type=f.file_type,
            file_size=f.file_size,
            mime_type=f.mime_type,
            extraction_status=f.extraction_status or "pending",
            extraction_error=f.extraction_error,
            extracted_at=_iso(f.extracted_at) if f.extracted_at else None,
            created_at=_iso(f.created_at),
            metadata=dict(f.file_metadata) if f.file_metadata else None,
            extracted_text=f.extracted_text,
        )
        file_store.create_file(project.path, record)
        summary.files += 1


def _write_gitignore(project_path: str) -> None:
    gi = paths.gitignore(project_path)
    if gi.exists():
        return
    atomic.write_text(gi, ".cache/\n*.tmp\n.migration_done\n")


def _seal_sentinel(project_path: str, summary: MigrationSummary) -> None:
    atomic.write_yaml(
        paths.migration_sentinel(project_path),
        {
            "schema_version": SCHEMA_VERSION,
            "migrated_at": datetime.now(timezone.utc).isoformat(),
            "counts": {
                "issues": summary.issues,
                "memories": summary.memories,
                "files": summary.files,
            },
        },
    )


def _iso(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep="T", timespec="seconds")
    return str(value)

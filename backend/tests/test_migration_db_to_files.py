from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio

from app.migration.db_to_files import migrate_project
from app.models.issue import Issue, IssueStatus
from app.models.issue_feedback import IssueFeedback
from app.models.issue_relation import IssueRelation, RelationType
from app.models.memory import Memory, MemoryLink
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.task import Task, TaskStatus
from app.storage import atomic, paths


@pytest_asyncio.fixture
async def project(db_session, tmp_path: Path) -> Project:
    p = Project(id="proj-test", name="Test", path=str(tmp_path), description="", tech_stack="")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


async def test_migrate_empty_project_creates_structure(db_session, project):
    summary = await migrate_project(db_session, project)
    assert summary.skipped is False
    assert summary.issues == 0
    assert summary.memories == 0
    assert summary.files == 0

    assert paths.manager_ai_root(project.path).exists()
    assert paths.issues_dir(project.path).exists()
    assert paths.memories_dir(project.path).exists()
    assert paths.files_dir(project.path).exists()
    assert paths.resources_dir(project.path).exists()
    assert paths.migration_sentinel(project.path).exists()
    assert paths.gitignore(project.path).exists()


async def test_migrate_issue_with_tasks_and_feedback(db_session, project):
    issue = Issue(
        id="i1",
        project_id=project.id,
        name="Test",
        description="desc body",
        status=IssueStatus.ACCEPTED,
        priority=1,
        specification="spec here",
        plan="plan here",
    )
    db_session.add(issue)
    await db_session.flush()

    db_session.add_all(
        [
            Task(id="t1", issue_id="i1", name="first", status=TaskStatus.PENDING, order=0),
            Task(id="t2", issue_id="i1", name="second", status=TaskStatus.IN_PROGRESS, order=1),
        ]
    )
    db_session.add(IssueFeedback(id="fb1", issue_id="i1", content="feedback body"))
    await db_session.commit()

    summary = await migrate_project(db_session, project)
    assert summary.issues == 1

    assert paths.issue_yaml(project.path, "i1").exists()
    data = atomic.read_yaml(paths.issue_yaml(project.path, "i1"))
    assert data["id"] == "i1"
    assert data["status"] == "Accepted"
    assert data["priority"] == 1
    assert [t["id"] for t in data["tasks"]] == ["t1", "t2"]

    assert paths.issue_md(project.path, "i1", "description").read_text(encoding="utf-8") == "desc body"
    assert paths.issue_md(project.path, "i1", "specification").read_text(encoding="utf-8") == "spec here"
    assert paths.issue_md(project.path, "i1", "plan").read_text(encoding="utf-8") == "plan here"
    assert not paths.issue_md(project.path, "i1", "recap").exists()

    fb_path = paths.issue_feedback_md(project.path, "i1", "fb1")
    assert fb_path.exists()
    assert "feedback body" in fb_path.read_text(encoding="utf-8")


async def test_migrate_issue_relations(db_session, project):
    db_session.add_all(
        [
            Issue(id="src", project_id=project.id, description="source", status=IssueStatus.NEW, priority=3),
            Issue(id="tgt", project_id=project.id, description="target", status=IssueStatus.NEW, priority=3),
        ]
    )
    await db_session.flush()
    db_session.add(IssueRelation(source_id="src", target_id="tgt", relation_type=RelationType.BLOCKS))
    await db_session.commit()

    await migrate_project(db_session, project)
    src_data = atomic.read_yaml(paths.issue_yaml(project.path, "src"))
    assert len(src_data["relations"]) == 1
    assert src_data["relations"][0] == {"target_id": "tgt", "type": "blocks", "created_at": src_data["relations"][0]["created_at"]}


async def test_migrate_memories_with_hierarchy_and_links(db_session, project):
    db_session.add_all(
        [
            Memory(id="root", project_id=project.id, title="Root", description="r body"),
            Memory(id="child", project_id=project.id, title="Child", description="c body", parent_id="root"),
            Memory(id="other", project_id=project.id, title="Other", description="o body"),
        ]
    )
    await db_session.flush()
    db_session.add(MemoryLink(from_id="root", to_id="other", relation="see_also"))
    await db_session.commit()

    summary = await migrate_project(db_session, project)
    assert summary.memories == 3

    child_path = paths.memory_md(project.path, "child")
    assert "parent_id: root" in child_path.read_text(encoding="utf-8")

    index = atomic.read_yaml(paths.memories_index(project.path))
    assert {e["id"] for e in index["memories"]} == {"root", "child", "other"}

    root_path = paths.memory_md(project.path, "root")
    root_content = root_path.read_text(encoding="utf-8")
    assert "to_id: other" in root_content
    assert "see_also" in root_content


async def test_migrate_files_with_extracted_text(db_session, project):
    db_session.add_all(
        [
            ProjectFile(
                id="f1",
                project_id=project.id,
                original_name="doc.pdf",
                stored_name="f1.pdf",
                file_type="pdf",
                file_size=100,
                mime_type="application/pdf",
                extracted_text="full text of pdf",
                extraction_status="ok",
                extracted_at=datetime.utcnow(),
            ),
            ProjectFile(
                id="f2",
                project_id=project.id,
                original_name="img.png",
                stored_name="f2.png",
                file_type="png",
                file_size=50,
                mime_type="image/png",
                extraction_status="skipped",
            ),
        ]
    )
    await db_session.commit()

    summary = await migrate_project(db_session, project)
    assert summary.files == 2

    index = atomic.read_yaml(paths.files_index(project.path))
    ids = {e["id"] for e in index["files"]}
    assert ids == {"f1", "f2"}
    assert paths.file_text_cache(project.path, "f1").exists()
    assert paths.file_text_cache(project.path, "f1").read_text(encoding="utf-8") == "full text of pdf"
    assert not paths.file_text_cache(project.path, "f2").exists()


async def test_migration_is_idempotent(db_session, project):
    db_session.add(Memory(id="m1", project_id=project.id, title="Only", description="body"))
    await db_session.commit()

    first = await migrate_project(db_session, project)
    assert first.memories == 1

    second = await migrate_project(db_session, project)
    assert second.skipped is True
    assert second.skip_reason == "already_migrated"


async def test_migration_skip_when_path_missing(db_session):
    project = Project(id="bad", name="Bad", path="/nonexistent/path/nowhere", description="", tech_stack="")
    db_session.add(project)
    await db_session.commit()

    summary = await migrate_project(db_session, project)
    assert summary.skipped is True
    assert summary.skip_reason == "path_missing"


async def test_migration_skip_when_already_populated(db_session, project):
    # Simulate fresh git clone: yaml already present, no sentinel
    atomic.ensure_dir(paths.manager_ai_root(project.path))
    atomic.write_yaml(paths.issues_index(project.path), {"schema_version": 1, "issues": []})

    db_session.add(Memory(id="m1", project_id=project.id, title="In DB", description="db body"))
    await db_session.commit()

    summary = await migrate_project(db_session, project)
    assert summary.skipped is True
    assert summary.skip_reason == "already_populated"
    # DB memory NOT dumped — existing layout is source of truth
    assert not paths.memory_md(project.path, "m1").exists()
    # Sentinel sealed so future runs skip cleanly
    assert paths.migration_sentinel(project.path).exists()

import pytest
import pytest_asyncio

from app.exceptions import NotFoundError, ValidationError
from app.models.issue_relation import RelationType
from app.schemas.issue_relation import make_relation_id
from app.services.issue_relation_service import IssueRelationService
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session, tmp_path):
    return await ProjectService(db_session).create(name="Test", path=str(tmp_path))


@pytest_asyncio.fixture
async def issues(db_session, project):
    svc = IssueService(db_session)
    return [
        await svc.create(project_id=project.id, description=f"Issue {i}")
        for i in range(4)
    ]


async def test_add_blocks_relation(db_session, issues):
    svc = IssueRelationService(db_session)
    rel = await svc.add_relation(issues[0].id, issues[1].id, RelationType.BLOCKS)
    assert rel.source_id == issues[0].id
    assert rel.target_id == issues[1].id
    assert rel.relation_type == RelationType.BLOCKS.value


async def test_add_related_normalizes_order(db_session, issues):
    svc = IssueRelationService(db_session)
    a, b = sorted([issues[0].id, issues[1].id])
    rel = await svc.add_relation(b, a, RelationType.RELATED)
    assert rel.source_id == a
    assert rel.target_id == b


async def test_self_relation_raises(db_session, issues):
    svc = IssueRelationService(db_session)
    with pytest.raises(ValidationError):
        await svc.add_relation(issues[0].id, issues[0].id, RelationType.BLOCKS)


async def test_cycle_detection(db_session, issues):
    svc = IssueRelationService(db_session)
    await svc.add_relation(issues[0].id, issues[1].id, RelationType.BLOCKS)
    await svc.add_relation(issues[1].id, issues[2].id, RelationType.BLOCKS)
    with pytest.raises(ValidationError):
        await svc.add_relation(issues[2].id, issues[0].id, RelationType.BLOCKS)


async def test_get_blockers(db_session, issues):
    svc = IssueRelationService(db_session)
    await svc.add_relation(issues[0].id, issues[1].id, RelationType.BLOCKS)
    blockers = await svc.get_blockers(issues[1].id)
    assert len(blockers) == 1
    assert blockers[0].source_id == issues[0].id


async def test_get_relations_for_issue(db_session, issues):
    svc = IssueRelationService(db_session)
    await svc.add_relation(issues[0].id, issues[1].id, RelationType.BLOCKS)
    await svc.add_relation(issues[0].id, issues[2].id, RelationType.RELATED)
    relations = await svc.get_relations_for_issue(issues[0].id)
    assert len(relations) == 2


async def test_delete_relation(db_session, issues):
    svc = IssueRelationService(db_session)
    rel = await svc.add_relation(issues[0].id, issues[1].id, RelationType.BLOCKS)
    rel_id = make_relation_id(rel.source_id, rel.target_id, rel.relation_type)
    await svc.delete_relation(rel_id, issues[0].id)
    relations = await svc.get_relations_for_issue(issues[0].id)
    assert len(relations) == 0

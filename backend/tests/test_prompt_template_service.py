import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models import PromptTemplate  # noqa: F401 — needed for table creation


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_resolve_falls_back_to_file(session, tmp_path):
    from app.services.prompt_template_service import PromptTemplateService

    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "workflow.md").write_text(
        "---\ntype: workflow\n---\nHello {{project_name}}", encoding="utf-8"
    )

    svc = PromptTemplateService(session, library_path=str(tmp_path))
    result = await svc.resolve("workflow", "proj-1", {"project_name": "MyApp"})
    assert result == "Hello MyApp"


@pytest.mark.asyncio
async def test_db_override_takes_priority(session, tmp_path):
    from app.models.prompt_template import PromptTemplate
    from app.services.prompt_template_service import PromptTemplateService

    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "workflow.md").write_text("---\ntype: workflow\n---\nFile content", encoding="utf-8")

    session.add(PromptTemplate(project_id="proj-1", type="workflow", content="DB override {{project_name}}"))
    await session.flush()

    svc = PromptTemplateService(session, library_path=str(tmp_path))
    result = await svc.resolve("workflow", "proj-1", {"project_name": "X"})
    assert result == "DB override X"


@pytest.mark.asyncio
async def test_no_template_returns_empty(session, tmp_path):
    from app.services.prompt_template_service import PromptTemplateService

    (tmp_path / "templates").mkdir()
    svc = PromptTemplateService(session, library_path=str(tmp_path))
    result = await svc.resolve("workflow", "proj-1", {})
    assert result == ""


@pytest.mark.asyncio
async def test_list_for_project_returns_all_types(session, tmp_path):
    from app.services.prompt_template_service import PromptTemplateService

    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    for t in ["workflow", "implementation", "recap", "spec", "plan", "enrich"]:
        (tpl_dir / f"{t}.md").write_text(f"---\ntype: {t}\n---\nContent", encoding="utf-8")

    svc = PromptTemplateService(session, library_path=str(tmp_path))
    result = await svc.list_for_project("proj-1")
    assert len(result) == 6
    types = {r.type for r in result}
    assert "workflow" in types
    assert "implementation" in types
    assert all(not r.is_overridden for r in result)


@pytest.mark.asyncio
async def test_save_and_delete_override(session, tmp_path):
    from app.services.prompt_template_service import PromptTemplateService

    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "workflow.md").write_text("---\ntype: workflow\n---\nDefault", encoding="utf-8")

    svc = PromptTemplateService(session, library_path=str(tmp_path))
    await svc.save_override("workflow", "proj-1", "Custom content")
    await session.flush()

    info = await svc.get_template_info("workflow", "proj-1")
    assert info.is_overridden is True
    assert info.content == "Custom content"

    await svc.delete_override("workflow", "proj-1")
    await session.flush()
    info2 = await svc.get_template_info("workflow", "proj-1")
    assert info2.is_overridden is False
    assert info2.content == "Default"

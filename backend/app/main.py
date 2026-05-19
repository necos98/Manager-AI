import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import async_session
from app.exceptions import AppError
from app.hooks import hook_registry
import app.hooks.handlers  # noqa: F401 — triggers @hook decorator registration
from app.mcp.server import mcp
from app.mcp.catalog import catalog_loader
from app.mcp.plugin_manager import plugin_manager
from app.migration.db_to_files import migrate_all_projects
from app.services.file_service import recover_pending_transcriptions
from app.services.manager_ai_watcher import manager_ai_watcher
from app.routers import activity, agents, credentials, events, files, issue_relations, issues, library, memories, network, pipelines, plugins, project_links, project_settings, project_skills, project_templates, project_variables, projects, settings as settings_router, system, tasks, terminals, terminal_commands

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    # Safety net: ensure ProactorEventLoop policy (supports subprocesses for MCP
    # stdio plugins). The primary fix is a .pth file (installed by start.py) that
    # patches uvicorn's asyncio_setup before it runs. This call catches the case
    # where the .pth patch didn't run (e.g. uvicorn started directly without
    # start.py). The running loop won't change, but future loops use the right policy.
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

@asynccontextmanager
async def _noop_lifespan(_app):
    """No-op lifespan for the mounted StreamableHTTP Starlette app.

    The real session-manager lifecycle is driven by the main FastAPI lifespan
    below (via mcp.session_manager.run()).  The mounted app MUST NOT have its
    own lifespan because Starlette does not enter Mounted-app lifespans and
    we don't want two callers competing for the single-run session manager.
    """
    yield


# Create the MCP StreamableHTTP ASGI app so the session manager is initialized.
_streamable_app = mcp.streamable_http_app()
# Clear the lifespan on the mounted app — we manage the session manager
# explicitly in the main lifespan.  Without this, Starlette may try to use
# the mounted app's lifespan (which also calls session_manager.run()),
# leading to "can only be called once" errors that tear down the task group.
_streamable_app.router.lifespan_context = _noop_lifespan


@asynccontextmanager
async def lifespan(app):
    logger.info("Hook registry: %d event(s) registered", len(hook_registry._hooks))
    for event_type, hooks in hook_registry._hooks.items():
        for h in hooks:
            logger.info("  %s -> %s", event_type.value, h.name)

    try:
        await migrate_all_projects(async_session)
    except Exception:
        logger.exception("DB → .manager_ai/ migration failed; continuing startup")

    rows = []
    try:
        from sqlalchemy import select
        from app.models.project import Project
        async with async_session() as session:
            rows = (
                await session.execute(
                    select(Project).where(Project.archived_at.is_(None))
                )
            ).scalars().all()
            for p in rows:
                await manager_ai_watcher.start_project(p.id, p.path, mcp=mcp, plugin_manager=plugin_manager)
    except Exception:
        logger.exception("Failed to start .manager_ai/ watchers; continuing startup")
    else:
        try:
            for p in rows:
                recover_pending_transcriptions(p.path)
        except Exception:
            logger.exception("Failed to recover pending transcriptions; continuing startup")
        catalog_loader.load()
        try:
            for p in rows:
                await plugin_manager.start_plugins_for_project(p.id, p.path, mcp)
        except Exception:
            logger.exception("Failed to start MCP plugins; continuing startup")

    async with mcp.session_manager.run():
        try:
            yield
        finally:
            try:
                for p in rows:
                    await plugin_manager.stop_plugins_for_project(p.id)
            except Exception:
                logger.exception("Failed to stop MCP plugins; continuing shutdown")
            await manager_ai_watcher.stop_all()


app = FastAPI(title="Manager AI", version="0.1.0", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(projects.dashboard_router)
app.include_router(project_links.router)
app.include_router(project_settings.router)
app.include_router(project_templates.router)
app.include_router(credentials.router)
app.include_router(files.formats_router)
app.include_router(files.router)
app.include_router(issues.router)
app.include_router(issue_relations.router)
app.include_router(tasks.router)
app.include_router(settings_router.router)
app.include_router(terminals.router)
app.include_router(terminal_commands.router)
app.include_router(project_variables.router)
app.include_router(agents.router)
app.include_router(pipelines.router)
app.include_router(events.router)
app.include_router(activity.router)
app.include_router(library.router)
app.include_router(memories.project_scoped)
app.include_router(memories.flat)
app.include_router(project_skills.router)
app.include_router(plugins.router)
app.include_router(plugins.catalog_router)
app.include_router(network.router)
app.include_router(system.router)

app.mount("/mcp", _streamable_app)


@app.get("/health")
async def health():
    return {"status": "ok"}

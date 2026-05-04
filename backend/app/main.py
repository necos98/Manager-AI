import logging
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
from app.migration.db_to_files import migrate_all_projects
from app.services.manager_ai_watcher import manager_ai_watcher
from app.routers import activity, events, files, issue_relations, issues, library, memories, network, project_settings, project_skills, project_templates, project_variables, projects, settings as settings_router, system, tasks, terminals, terminal_commands

logger = logging.getLogger(__name__)

mcp_app = mcp.streamable_http_app()


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
                await manager_ai_watcher.start_project(p.id, p.path)
    except Exception:
        logger.exception("Failed to start .manager_ai/ watchers; continuing startup")

    async with mcp.session_manager.run():
        try:
            yield
        finally:
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
app.include_router(project_settings.router)
app.include_router(project_templates.router)
app.include_router(files.formats_router)
app.include_router(files.router)
app.include_router(issues.router)
app.include_router(issue_relations.router)
app.include_router(tasks.router)
app.include_router(settings_router.router)
app.include_router(terminals.router)
app.include_router(terminal_commands.router)
app.include_router(project_variables.router)
app.include_router(events.router)
app.include_router(activity.router)
app.include_router(library.router)
app.include_router(memories.project_scoped)
app.include_router(memories.flat)
app.include_router(project_skills.router)
app.include_router(network.router)
app.include_router(system.router)

app.mount("/mcp", mcp_app)


@app.get("/health")
async def health():
    return {"status": "ok"}

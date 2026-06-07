import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.requests import ClientDisconnect

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
from app.storage.memory_store_core import memory_store
from app.storage.write_queue import WriteQueue
from app.storage.background_writer import BackgroundWriter
from app.storage import memory_store as memory_store_module
from app.storage import issue_store as issue_store_module
from app.storage import file_store as file_store_module
from app.middleware import ErrorLoggerMiddleware
from app.routers import activity, agents, credentials, credentials_editor, events, files, issue_relations, issues, library, memories, network, pipeline_runs, pipelines, plugins, project_links, project_settings, project_skills, project_templates, project_variables, projects, questions, settings as settings_router, system, tasks, terminals, terminal_commands
from app.routers.projects import install_claude_resources_to
from cryptography.fernet import Fernet

from app.storage.project_loader import _load_project_into_memory
from sqlalchemy import select, update
from app.models.issue import Issue
from app.models.project import Project
from app.services.agent_service import AgentService
from app.services.pipeline_service import PipelineService
from app.models.pipeline_run import PipelineRun, PipelineRunStatus
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class _SuppressClientDisconnectFilter(logging.Filter):
    """Suppress log records whose exception is a ClientDisconnect.

    Client disconnects are normal — logging them at ERROR is noise.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info:
            exc_type = record.exc_info[0]
            if exc_type is not None and exc_type.__name__ == "ClientDisconnect":
                return False
        return True

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

    def _suppress_windows_accept_noise(loop, context):
        """Demote known Windows IOCP accept noise to DEBUG level.

        WinError 64  — network name no longer available (client disconnected mid-handshake)
        WinError 121 — semaphore timeout (legitimate timeout, not a crash)
        WinError 122 — data area passed to system call is too small
        WinError 995 — I/O operation aborted (socket closed during accept)
        WinError 1236 — network connection aborted by local system
        """
        exc = context.get("exception")
        if isinstance(exc, OSError) and getattr(exc, "winerror", None) in (64, 121, 122, 995, 1236):
            logger.debug("Suppressed Windows accept noise: %r", exc)
            return
        loop.default_exception_handler(context)

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

# Suppress ERROR logs for ClientDisconnect in the MCP streamable HTTP handler.
# Client disconnects are normal — the library logs them at ERROR with full
# traceback via logger.exception, which is noise.
logging.getLogger("mcp.server.streamable_http").addFilter(
    _SuppressClientDisconnectFilter()
)

# Catch any ClientDisconnect that escapes the MCP handler (e.g. from a failed
# error-response send after the client already disconnected).
@_streamable_app.exception_handler(ClientDisconnect)
async def _client_disconnect_handler(request, exc):
    logger.debug("Client disconnected during MCP request to %s", request.url.path)
    return Response(status_code=499)


def _startup_resolve_secret_key() -> None:
    if not os.environ.get("MANAGER_AI_SECRET_KEY"):
        key_path = os.path.join("data", "secret.key")
        if os.path.exists(key_path):
            with open(key_path, "r") as f:
                os.environ["MANAGER_AI_SECRET_KEY"] = f.read().strip()
            logger.info("Loaded MANAGER_AI_SECRET_KEY from %s", key_path)
        else:
            key = Fernet.generate_key().decode()
            os.environ["MANAGER_AI_SECRET_KEY"] = key
            tmp_path = key_path + ".tmp"
            with open(tmp_path, "w") as f:
                f.write(key + "\n")
            os.replace(tmp_path, key_path)
            logger.info("Generated and persisted MANAGER_AI_SECRET_KEY to %s", key_path)


def _startup_log_hooks() -> None:
    logger.info("Hook registry: %d event(s) registered", len(hook_registry._hooks))
    for event_type, hooks in hook_registry._hooks.items():
        for h in hooks:
            logger.info("  %s -> %s", event_type.value, h.name)


async def _startup_migrate(db_session) -> None:
    try:
        await migrate_all_projects(db_session)
    except Exception:
        logger.exception("DB → .manager_ai/ migration failed; continuing startup")


async def _startup_fixup_statuses(db_session) -> None:
    _STATUS_FIXUP_MAP: dict[str, str] = {
        "Completed": "Finished",
    }
    try:
        async with db_session() as session:
            for bad_val, good_val in _STATUS_FIXUP_MAP.items():
                stmt = select(Issue.id).where(Issue.status == bad_val)
                result = await session.execute(stmt)
                ids = result.scalars().all()
                if ids:
                    upd = (
                        update(Issue)
                        .where(Issue.status == bad_val)
                        .values(status=good_val)
                    )
                    await session.execute(upd)
                    await session.commit()
                    logger.warning(
                        "Startup fixup: migrated %d issue(s) from status '%s' to '%s'",
                        len(ids), bad_val, good_val,
                    )
    except Exception:
        logger.exception("Status fixup failed; continuing startup")


def _startup_init_write_queue() -> tuple[WriteQueue, BackgroundWriter]:
    write_queue = WriteQueue("data/pending_writes.db")
    background_writer = BackgroundWriter(write_queue)
    return write_queue, background_writer


async def _startup_load_projects(db_session, write_queue, background_writer) -> list:
    memory_store_module.inject_write_queue(write_queue)
    issue_store_module.inject_write_queue(write_queue)
    file_store_module.inject_write_queue(write_queue)
    async with db_session() as session:
        rows = (
            await session.execute(
                select(Project).where(Project.archived_at.is_(None))
            )
        ).scalars().all()
        for p in rows:
            _load_project_into_memory(p.path, memory_store)
    if rows:
        await background_writer.start()
    return rows


async def _startup_recover_transcriptions(rows: list) -> None:
    try:
        for p in rows:
            recover_pending_transcriptions(p.path)
    except Exception:
        logger.exception("Failed to recover pending transcriptions; continuing startup")


def _startup_load_catalog() -> None:
    catalog_loader.load()


async def _startup_plugins(rows: list, mcp_server) -> None:
    try:
        for p in rows:
            await plugin_manager.start_plugins_for_project(p.id, p.path, mcp_server)
    except Exception:
        logger.exception("Failed to start MCP plugins; continuing startup")


async def _startup_seed_defaults(db_session) -> None:
    try:
        async with db_session() as seed_session:
            try:
                await AgentService(seed_session).seed_defaults()
                await seed_session.commit()
            except Exception:
                await seed_session.rollback()
                logger.warning("Failed to seed default agents", exc_info=True)
            try:
                await PipelineService(seed_session).seed_defaults()
                await seed_session.commit()
            except Exception:
                await seed_session.rollback()
                logger.warning("Failed to seed default pipelines", exc_info=True)
    except Exception:
        logger.exception("Failed to seed default agents/pipelines; continuing startup")


async def _startup_cleanup_orphaned_runs(db_session) -> None:
    try:
        async with db_session() as cleanup_session:
            orphaned = await cleanup_session.execute(
                select(PipelineRun).where(
                    PipelineRun.status == PipelineRunStatus.RUNNING
                )
            )
            count = 0
            for run in orphaned.scalars().all():
                run.status = PipelineRunStatus.FAILED
                run.finished_at = datetime.now(timezone.utc)
                count += 1
            if count:
                await cleanup_session.commit()
                logger.warning(
                    "Startup cleanup: marked %d orphaned pipeline run(s) as FAILED",
                    count,
                )
    except Exception:
        logger.exception("Failed to cleanup orphaned pipeline runs; continuing startup")


async def _startup_install_claude_resources(rows: list) -> None:
    try:
        for p in rows:
            try:
                result = install_claude_resources_to(p.path)
                logger.info("Installed claude_resources to %s: %s", p.path, result.get("copied"))
            except Exception:
                logger.warning("Failed to install claude_resources to %s", p.path, exc_info=True)
    except Exception:
        logger.exception("Failed to install claude_resources; continuing startup")


async def _shutdown(rows: list, background_writer, write_queue) -> None:
    try:
        for p in rows:
            await plugin_manager.stop_plugins_for_project(p.id)
    except Exception:
        logger.exception("Failed to stop MCP plugins; continuing shutdown")
    await background_writer.stop()
    write_queue.close()


@asynccontextmanager
async def lifespan(app):
    if sys.platform == "win32":
        asyncio.get_running_loop().set_exception_handler(_suppress_windows_accept_noise)

    _startup_resolve_secret_key()
    _startup_log_hooks()
    await _startup_migrate(async_session)
    await _startup_fixup_statuses(async_session)
    wq, bw = _startup_init_write_queue()
    rows = await _startup_load_projects(async_session, wq, bw)
    try:
        await _startup_recover_transcriptions(rows)
        _startup_load_catalog()
        await _startup_plugins(rows, mcp)
        await _startup_seed_defaults(async_session)
        await _startup_cleanup_orphaned_runs(async_session)
        await _startup_install_claude_resources(rows)
    except Exception:
        logger.exception("Non-critical startup ops failed; continuing")

    async with mcp.session_manager.run():
        try:
            yield
        finally:
            await _shutdown(rows, bw, wq)


app = FastAPI(title="Manager AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(ErrorLoggerMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(pipelines.router)
app.include_router(pipeline_runs.router)
app.include_router(projects.router)
app.include_router(projects.dashboard_router)
app.include_router(project_links.router)
app.include_router(project_settings.router)
app.include_router(project_templates.router)
app.include_router(credentials.router)
app.include_router(credentials_editor.router)
app.include_router(files.formats_router)
app.include_router(files.router)
app.include_router(issues.router)
app.include_router(issue_relations.router)
app.include_router(issue_relations.batch_router)
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
app.include_router(plugins.router)
app.include_router(plugins.catalog_router)
app.include_router(network.router)
app.include_router(questions.router)
app.include_router(system.router)

app.mount("/mcp", _streamable_app)


@app.get("/health")
async def health():
    return {"status": "ok"}

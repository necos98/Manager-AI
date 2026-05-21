import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

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
from app.storage.memory_store_core import memory_store
from app.storage.write_queue import WriteQueue
from app.storage.background_writer import BackgroundWriter
from app.storage import memory_store as memory_store_module
from app.storage import issue_store as issue_store_module
from app.storage import file_store as file_store_module
from app.routers import activity, agents, credentials, events, files, issue_relations, issues, library, memories, network, pipelines, plugins, project_links, project_settings, project_skills, project_templates, project_variables, projects, questions, settings as settings_router, system, tasks, terminals, terminal_commands

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


def _load_project_into_memory(project_path: str, store: Any) -> None:
    """Load all issues, memories, and file metadata from disk into MemoryStore."""
    import re as _re
    from app.storage import atomic as _atomic, paths as _paths

    _FRONTMATTER_RE = _re.compile(r"^---\n(.*?)\n---\n?(.*)$", _re.DOTALL)

    def _parse_fm(text: str) -> dict[str, Any]:
        if not text:
            return {"meta": {}, "body": ""}
        m = _FRONTMATTER_RE.match(text)
        if not m:
            return {"meta": {}, "body": text}
        import yaml as _yaml
        meta = _yaml.safe_load(m.group(1)) or {}
        return {"meta": meta, "body": m.group(2)}

    # --- memories ---
    mem_dir = _paths.memories_dir(project_path)
    mem_records: dict[str, Any] = {}
    mem_index: list[dict[str, Any]] = []
    if mem_dir.exists():
        for md_file in mem_dir.glob("*.md"):
            try:
                parsed = _parse_fm(_atomic.read_text(md_file))
                meta = parsed["meta"] or {}
                body = parsed["body"]
                mid = str(meta.get("id", md_file.stem))
                from app.storage.memory_store import MemoryRecord, MemoryLinkRecord

                def _opt_str(v: Any) -> str | None:
                    if v is None:
                        return None
                    s = str(v)
                    return s if s else None

                def _as_str(v: Any) -> str:
                    if v is None:
                        return ""
                    return str(v)

                def _link_from_dict(d: dict) -> Any:
                    return MemoryLinkRecord(
                        to_id=str(d.get("to_id", "")),
                        relation=str(d.get("relation", "")),
                        created_at=_as_str(d.get("created_at")),
                    )

                record = MemoryRecord(
                    id=mid,
                    project_id=str(meta.get("project_id", "")),
                    title=str(meta.get("title", "")),
                    parent_id=_opt_str(meta.get("parent_id")),
                    description=body,
                    created_at=_as_str(meta.get("created_at")),
                    updated_at=_as_str(meta.get("updated_at")),
                    links=[_link_from_dict(l) for l in (meta.get("links") or [])],
                )
                mem_records[mid] = record
                mem_index.append({
                    "id": mid,
                    "project_id": str(meta.get("project_id", "")),
                    "title": str(meta.get("title", "")),
                    "parent_id": _opt_str(meta.get("parent_id")),
                    "created_at": _as_str(meta.get("created_at")),
                    "updated_at": _as_str(meta.get("updated_at")),
                    "links": list(meta.get("links") or []),
                })
            except Exception:
                logger.warning("Skipping corrupted memory file: %s", md_file, exc_info=True)
    mem_index.sort(key=lambda e: (e["created_at"], e["id"]))
    store.init_project(project_path, "memories", mem_records, mem_index)

    # --- issues ---
    issues_dir = _paths.issues_dir(project_path)
    issue_records: dict[str, Any] = {}
    issue_index: list[dict[str, Any]] = []
    if issues_dir.exists():
        for issue_folder in issues_dir.iterdir():
            if not issue_folder.is_dir():
                continue
            yaml_path = issue_folder / "issue.yaml"
            if not yaml_path.exists():
                continue
            try:
                data = _atomic.read_yaml(yaml_path) or {}
                iid = data.get("id", issue_folder.name)
                description = _atomic.read_text(_paths.issue_md(project_path, iid, "description"))
                specification = _read_optional_md(_atomic, _paths, project_path, iid, "specification")
                plan = _read_optional_md(_atomic, _paths, project_path, iid, "plan")
                recap = _read_optional_md(_atomic, _paths, project_path, iid, "recap")
                from app.storage.issue_store import IssueRecord, TaskRecord, RelationRecord

                record = IssueRecord(
                    id=iid,
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
                issue_records[iid] = record
                issue_index.append({
                    "id": iid,
                    "project_id": data.get("project_id", ""),
                    "name": data.get("name"),
                    "status": data.get("status", "New"),
                    "priority": int(data.get("priority", 3)),
                    "created_at": _as_iso(data.get("created_at")),
                    "updated_at": _as_iso(data.get("updated_at")),
                })
            except Exception:
                logger.warning("Skipping corrupted issue: %s", issue_folder, exc_info=True)
    issue_index.sort(key=lambda e: (e["created_at"], e["id"]))
    store.init_project(project_path, "issues", issue_records, issue_index)

    # --- files ---
    files_index_path = _paths.files_index(project_path)
    file_records: dict[str, Any] = {}
    file_index: list[dict[str, Any]] = []
    if files_index_path.exists():
        try:
            data = _atomic.read_yaml(files_index_path) or {}
            entries = list(data.get("files") or [])
            from app.storage.file_store import FileRecord

            for e in entries:
                fid = str(e.get("id", ""))
                record = FileRecord(
                    id=fid,
                    original_name=str(e.get("original_name", "")),
                    stored_name=str(e.get("stored_name", "")),
                    file_type=str(e.get("file_type", "")),
                    file_size=int(e.get("file_size", 0)),
                    mime_type=str(e.get("mime_type", "")),
                    extraction_status=str(e.get("extraction_status", "pending")),
                    extraction_error=_opt_str_static(e.get("extraction_error")),
                    extracted_at=_opt_str_static(e.get("extracted_at")),
                    created_at=_as_iso(e.get("created_at")),
                    metadata=e.get("metadata") if isinstance(e.get("metadata"), dict) else None,
                    extracted_text=None,
                )
                file_records[fid] = record
                file_index.append({
                    "id": fid,
                    "original_name": e.get("original_name", ""),
                    "stored_name": e.get("stored_name", ""),
                    "file_type": e.get("file_type", ""),
                    "file_size": int(e.get("file_size", 0)),
                    "mime_type": e.get("mime_type", ""),
                    "extraction_status": e.get("extraction_status", "pending"),
                    "extraction_error": e.get("extraction_error"),
                    "extracted_at": e.get("extracted_at"),
                    "created_at": e.get("created_at", ""),
                    "metadata": e.get("metadata"),
                })
        except Exception:
            logger.warning("Skipping corrupted files index: %s", files_index_path, exc_info=True)
    store.init_project(project_path, "files", file_records, file_index)

    logger.info(
        "Loaded project %s: %d memories, %d issues, %d files",
        project_path, len(mem_records), len(issue_records), len(file_records),
    )


# Helpers used by _load_project_into_memory — defined at module level to keep the function clean

def _read_optional_md(_atomic, _paths, project_path: str, issue_id: str, field_name: str) -> str | None:
    path = _paths.issue_md(project_path, issue_id, field_name)
    if not path.exists():
        return None
    return _atomic.read_text(path)


def _opt_str_static(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value)
    return s if s else None


def _as_iso(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _task_from_dict(d: dict) -> Any:
    from app.storage.issue_store import TaskRecord
    return TaskRecord(
        id=str(d.get("id", "")),
        name=str(d.get("name", "")),
        status=str(d.get("status", "Pending")),
        order=int(d.get("order", 0)),
        created_at=_as_iso(d.get("created_at")),
        updated_at=_as_iso(d.get("updated_at")),
    )


def _relation_from_dict(d: dict) -> Any:
    from app.storage.issue_store import RelationRecord
    return RelationRecord(
        target_id=str(d.get("target_id", "")),
        type=str(d.get("type", "related")),
        created_at=_as_iso(d.get("created_at")),
    )


@asynccontextmanager
async def lifespan(app):
    if sys.platform == "win32":
        asyncio.get_running_loop().set_exception_handler(_suppress_windows_accept_noise)

    logger.info("Hook registry: %d event(s) registered", len(hook_registry._hooks))
    for event_type, hooks in hook_registry._hooks.items():
        for h in hooks:
            logger.info("  %s -> %s", event_type.value, h.name)

    try:
        await migrate_all_projects(async_session)
    except Exception:
        logger.exception("DB → .manager_ai/ migration failed; continuing startup")

    # Init write queue and background writer
    write_queue = WriteQueue("data/pending_writes.db")
    background_writer = BackgroundWriter(write_queue)

    # Inject write_queue into store modules so they can enqueue writes
    memory_store_module.inject_write_queue(write_queue)
    issue_store_module.inject_write_queue(write_queue)
    file_store_module.inject_write_queue(write_queue)

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
                _load_project_into_memory(p.path, memory_store)
        if rows:
            await background_writer.start()
    except Exception:
        logger.exception("Failed to load projects into memory; continuing startup")
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
            await background_writer.stop()
            write_queue.close()


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
app.include_router(questions.router)
app.include_router(system.router)

app.mount("/mcp", _streamable_app)


@app.get("/health")
async def health():
    return {"status": "ok"}

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.hooks import hook_registry
import app.hooks.handlers  # noqa: F401 — triggers @hook decorator registration
from app.mcp.server import mcp
from app.routers import events, files, issues, projects, settings, tasks, terminals, terminal_commands

logger = logging.getLogger(__name__)

mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app):
    logger.info("Hook registry: %d event(s) registered", len(hook_registry._hooks))
    for event, hooks in hook_registry._hooks.items():
        for h in hooks:
            logger.info("  %s -> %s", event.value, h.name)
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Manager AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(files.router)
app.include_router(issues.router)
app.include_router(tasks.router)
app.include_router(settings.router)
app.include_router(terminals.router)
app.include_router(terminal_commands.router)
app.include_router(events.router)

app.mount("/mcp", mcp_app)


@app.get("/health")
async def health():
    return {"status": "ok"}

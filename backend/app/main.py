from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.mcp.server import mcp
from app.routers import projects, tasks

# Get the MCP Starlette sub-app (creates session manager lazily)
mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Manager AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(tasks.router)

# Mount MCP sub-app at /mcp (sub-app routes at / internally)
app.mount("/mcp", mcp_app)


@app.get("/health")
async def health():
    return {"status": "ok"}

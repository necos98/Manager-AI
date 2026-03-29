import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import AppError
from app.hooks import hook_registry
import app.hooks.handlers  # noqa: F401 — triggers @hook decorator registration
from app.mcp.server import mcp
from app.rag import set_rag_service
from app.rag.chunker import TextChunker
from app.rag.drivers.sentence_transformer import SentenceTransformerDriver
from app.rag.extractors.base import ExtractorRegistry
from app.rag.extractors.txt_extractor import TxtExtractor
from app.rag.extractors.pdf_extractor import PdfExtractor
from app.rag.pipeline import EmbeddingPipeline
from app.rag.store import VectorStore
from app.routers import activity, events, files, issue_relations, issues, library, network, project_settings, project_skills, project_templates, project_variables, projects, settings as settings_router, tasks, terminals, terminal_commands
from app.services.event_service import event_service
from app.services.rag_service import RagService

logger = logging.getLogger(__name__)

mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app):
    logger.info("Hook registry: %d event(s) registered", len(hook_registry._hooks))
    for event_type, hooks in hook_registry._hooks.items():
        for h in hooks:
            logger.info("  %s -> %s", event_type.value, h.name)

    # Initialize RAG pipeline
    registry = ExtractorRegistry()
    registry.register(TxtExtractor())
    registry.register(PdfExtractor())

    driver = SentenceTransformerDriver(model_name=settings.embedding_model)
    chunker = TextChunker(
        max_tokens=settings.chunk_max_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )
    store = VectorStore(db_path=settings.lancedb_path)
    pipeline = EmbeddingPipeline(
        registry=registry, chunker=chunker, driver=driver, store=store
    )
    rag_service = RagService(pipeline=pipeline, event_service=event_service)
    set_rag_service(rag_service)
    logger.info("RAG pipeline initialized (driver=%s, model=%s)", settings.embedding_driver, settings.embedding_model)

    async with mcp.session_manager.run():
        yield

    set_rag_service(None)


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
app.include_router(project_skills.router)
app.include_router(network.router)

app.mount("/mcp", mcp_app)


@app.get("/health")
async def health():
    return {"status": "ok"}

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.terminal import (
    AskTerminalCreate,
    HermesTerminalCreate,
    LogTerminalCreate,
    ManageAgentTerminalCreate,
    TerminalCreate,
    TerminalListResponse,
    TerminalResponse,
)
from app.services import terminal_handler
from app.services import terminal_operations as ops
from app.services.terminal_service import TerminalService, terminal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terminals", tags=["terminals"])


def get_terminal_service() -> TerminalService:
    return terminal_service


@router.post("", response_model=TerminalResponse, status_code=201)
async def create_terminal(
    data: TerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    return await ops.create_terminal(data, db, service)


@router.post("/ask", response_model=TerminalResponse, status_code=201)
async def create_ask_terminal(
    data: AskTerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    return await ops.create_ask_terminal(data, db, service)


@router.post("/manage-agent", response_model=TerminalResponse, status_code=201)
async def create_manage_agent_terminal(
    data: ManageAgentTerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    return await ops.create_manage_agent_terminal(data, db, service)


@router.post("/log", response_model=TerminalResponse, status_code=201)
async def create_log_terminal(
    data: LogTerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    return await ops.create_log_terminal(data, db, service)


@router.post("/hermes", response_model=TerminalResponse, status_code=201)
async def create_hermes_terminal(
    data: HermesTerminalCreate,
    service: TerminalService = Depends(get_terminal_service),
):
    return await ops.create_hermes_terminal(data, service)


# NOTE: /ask, /manage-agent, /config, /count MUST be defined before
# /{terminal_id} routes to avoid FastAPI matching them as path params.


@router.get("/ask", response_model=list[TerminalListResponse])
async def list_ask_terminals(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    return await ops.list_ask_terminals(project_id, db, service)


@router.get("/manage-agent", response_model=list[TerminalListResponse])
async def list_manage_agent_terminals(
    service: TerminalService = Depends(get_terminal_service),
):
    return ops.list_manage_agent_terminals(service)


@router.get("/config")
async def terminal_config(
    db: AsyncSession = Depends(get_db),
):
    return await ops.terminal_config(db)


@router.get("", response_model=list[TerminalListResponse])
async def list_terminals(
    project_id: str | None = Query(None),
    issue_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    return await ops.list_terminals(project_id, issue_id, db, service)


@router.get("/count")
async def terminal_count(
    service: TerminalService = Depends(get_terminal_service),
):
    return ops.terminal_count(service)


@router.get("/{terminal_id}/recording")
async def get_terminal_recording(
    terminal_id: str,
    service: TerminalService = Depends(get_terminal_service),
):
    return await ops.get_terminal_recording(terminal_id, service)


@router.delete("/{terminal_id}", status_code=204)
async def delete_terminal(
    terminal_id: str,
    service: TerminalService = Depends(get_terminal_service),
):
    await ops.delete_terminal(terminal_id, service)


@router.websocket("/{terminal_id}/ws")
async def terminal_ws(
    terminal_id: str,
    websocket: WebSocket,
    service: TerminalService = Depends(get_terminal_service),
):
    await terminal_handler.terminal_ws(terminal_id, websocket, service)

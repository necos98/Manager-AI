"""Terminal session lifecycle: reader, buffering, and close-signalling.

Extracted from ``app.routers.terminals`` so that the pipeline executor can
create PTY-backed command terminals and await completion without depending
on the HTTP/WS layer.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings as app_settings

if TYPE_CHECKING:
    from fastapi import WebSocket

    from app.services.terminal_service import TerminalService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Terminal session dataclass
# ---------------------------------------------------------------------------


@dataclass
class TerminalSession:
    """Mutable holder for the WebSocket, reader task, and a close-signalling event.

    Only the WS endpoint is allowed to close the WebSocket (in its ``finally``
    block).  The reader merely sets *pty_dead* so the endpoint can exit its
    receive loop gracefully — **and** so that an external waiter (e.g. the
    pipeline executor) can detect process completion.
    """

    ws: WebSocket | None = None
    reader_task: asyncio.Task[None] | None = None
    pty_dead: asyncio.Event = field(default_factory=asyncio.Event)
    pty_died_naturally: bool = False  # True when the PTY exited on its own


# ---------------------------------------------------------------------------
# Module-level shared state
# ---------------------------------------------------------------------------

# Dedicated thread pool for blocking PTY reads so they don't starve
# the default asyncio executor used by DB queries, HTTP, etc.
_pty_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="pty-read")

# One TerminalSession per terminal keeps the reader task, the WebSocket,
# and a pty_dead signal together so they never race.
_sessions: dict[str, TerminalSession] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _save_recording(terminal_id: str, content: str) -> None:
    """Write terminal output buffer to a file in the recordings directory."""
    if not content:
        return
    try:
        rec_dir = Path(app_settings.recordings_path)
        rec_dir.mkdir(parents=True, exist_ok=True)
        (rec_dir / f"{terminal_id}.txt").write_text(content, encoding="utf-8")
    except Exception:
        logger.warning(
            "Failed to save recording for terminal %s", terminal_id, exc_info=True
        )


# ---------------------------------------------------------------------------
# Persistent reader
# ---------------------------------------------------------------------------


async def _terminal_reader(
    terminal_id: str, service: TerminalService
) -> None:
    """Persistent reader: buffers PTY or log-queue output and forwards to a
    connected WebSocket.

    The reader never closes the WebSocket itself -- it only signals
    *pty_dead* on the TerminalSession when the underlying process exits.
    The WS endpoint is the sole owner of the close handshake.
    """
    session = _sessions.get(terminal_id)
    if session is None:
        return

    loop = asyncio.get_running_loop()
    with service._lock:
        entry = service._terminals.get(terminal_id)
    if entry is None:
        return

    is_log = entry.get("mode") == "log"

    try:
        if is_log:
            with service._lock:
                q = service._queues.get(terminal_id)
            if q is None:
                return
            while True:
                data = await q.get()
                if data is None:
                    # EOF sentinel - log terminal destroyed
                    buf = service.get_buffered_output(terminal_id)
                    _save_recording(terminal_id, buf)
                    service.mark_closed(terminal_id)
                    session.pty_died_naturally = True
                    session.pty_dead.set()  # signal WS endpoint / pipeline waiter
                    break
                service.append_output(terminal_id, data)
                ws = session.ws
                if ws:
                    try:
                        await ws.send_text(data)
                    except Exception:
                        session.ws = None
        else:
            try:
                pty = service.get_pty(terminal_id)
            except KeyError:
                return
            while True:
                data = await loop.run_in_executor(
                    _pty_executor, lambda: pty.read(blocking=True)
                )
                if not data:
                    # PTY EOF - process exited
                    buf = service.get_buffered_output(terminal_id)
                    _save_recording(terminal_id, buf)
                    service.mark_closed(terminal_id)
                    session.pty_died_naturally = True
                    session.pty_dead.set()  # signal WS endpoint / pipeline waiter
                    break
                service.append_output(terminal_id, data)
                ws = session.ws
                if ws:
                    try:
                        await ws.send_text(data)
                    except Exception:
                        # WebSocket gone - stop forwarding, but keep buffering
                        session.ws = None
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.warning(
            "Terminal reader error for %s", terminal_id, exc_info=True
        )
    finally:
        if session is not None:
            session.reader_task = None


def _ensure_reader(terminal_id: str, service: TerminalService) -> None:
    """Start the persistent reader if it is not already running."""
    session = _sessions.get(terminal_id)
    if session is None:
        return
    existing = session.reader_task
    if existing and not existing.done():
        return
    session.reader_task = asyncio.create_task(
        _terminal_reader(terminal_id, service)
    )


def _stop_reader(terminal_id: str) -> None:
    """Cancel the persistent reader for a terminal."""
    session = _sessions.get(terminal_id)
    if session is None:
        return
    task = session.reader_task
    session.reader_task = None
    if task and not task.done():
        task.cancel()

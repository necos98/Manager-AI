"""WebSocket handler for terminal PTY ↔ client I/O."""

from __future__ import annotations

import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.services.terminal_session import (
    TerminalSession,
    _ensure_reader,
    _sessions,
)

logger = logging.getLogger(__name__)


async def terminal_ws(
    terminal_id: str,
    websocket: WebSocket,
    service,  # TerminalService
) -> None:
    """Handle WebSocket ↔ PTY I/O for a terminal session.

    Accepts the WebSocket, replays buffered output, relays PTY ↔ client,
    and cleans up on disconnect or PTY death.
    """
    try:
        service.get(terminal_id)
    except KeyError:
        await websocket.close(code=4004, reason="Terminal not found")
        return

    await websocket.accept()
    pty = service.get_pty(terminal_id)

    # Replay buffered output so reconnecting clients see previous content
    buffered = service.get_buffered_output(terminal_id)
    if buffered:
        await websocket.send_text(buffered)
    elif pty is None:
        await websocket.send_text(
            "\x1b[90mConnected to agent output stream...\x1b[0m\r\n"
        )

    # Get or create the TerminalSession and register this WS on it.
    session = _sessions.get(terminal_id)
    if session is None:
        session = TerminalSession()
        _sessions[terminal_id] = session
    session.pty_dead.clear()
    session.pty_died_naturally = False
    session.ws = websocket
    _ensure_reader(terminal_id, service)

    # WebSocket ↔ PTY input loop
    try:
        while True:
            if session.pty_dead.is_set():
                break

            message = await websocket.receive_text()
            if message.startswith('{"type":"resize"'):
                try:
                    msg = json.loads(message)
                    if msg.get("type") == "resize":
                        service.resize(
                            terminal_id, msg["cols"], msg["rows"]
                        )
                        continue
                except (json.JSONDecodeError, KeyError):
                    pass
            if pty is not None:
                pty.write(message)
    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception:
        logger.warning(
            "ws_to_pty error for terminal %s", terminal_id, exc_info=True
        )
    finally:
        pty_ended_naturally = (
            session is not None and session.pty_died_naturally
        )
        if session is not None:
            session.ws = None
        close_code = 1000 if pty_ended_naturally else 1001
        try:
            await websocket.close(
                code=close_code, reason="Terminal session ended"
            )
        except Exception:
            pass

"""Terminal lifecycle management for pipeline steps.

ELIMINA LA DUPLICAZIONE: Le 4 operazioni di cleanup terminale
(_save_recording, _stop_reader, _sessions.pop, terminal_service.kill)
ora vivono in un unico posto.
"""

from app.services.terminal_service import terminal_service
from app.services.terminal_session import _save_recording, _sessions, _stop_reader


def cleanup_terminal(term_id: str) -> None:
    """Save recording, stop reader, remove session, and kill PTY."""
    if not term_id:
        return
    _save_recording(term_id, terminal_service.get_buffered_output(term_id))
    _stop_reader(term_id)
    _sessions.pop(term_id, None)
    terminal_service.kill(term_id)

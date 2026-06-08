"""Module-level step completion event signaling.

Orchestrates the interaction between the auto-mode _execute loop,
orchestrated-mode _monitor_step, and the MCP finished_pipeline_step tool.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

# Maps (run_id, step_index) -> asyncio.Event for step completion signaling
_completion_events: dict[tuple[str, int], asyncio.Event] = {}


def set_step_completed(run_id: str, step_index: int) -> bool:
    """Signal that a pipeline step has completed. Called by finished_pipeline_step MCP tool."""
    key = (run_id, step_index)
    event = _completion_events.get(key)
    if event is None:
        return False
    event.set()
    return True


def register_completion_event(run_id: str, step_index: int) -> asyncio.Event:
    """Create and register a completion event for a step."""
    event = asyncio.Event()
    _completion_events[(run_id, step_index)] = event
    return event


def get_completion_event(run_id: str, step_index: int) -> asyncio.Event | None:
    """Get a registered completion event, or None."""
    return _completion_events.get((run_id, step_index))


def unregister_completion_event(run_id: str, step_index: int) -> None:
    """Remove a completion event."""
    _completion_events.pop((run_id, step_index), None)

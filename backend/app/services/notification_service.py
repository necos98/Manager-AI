"""Notification service — sends Telegram notifications via Hermes CLI.

Listens to Manager AI events (via EventService) and spawns a lightweight
``hermes chat -q`` subprocess to deliver notifications on Telegram.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.providers.hermes_provider import HermesProvider
from app.services.event_service import BaseNotifier, event_service

logger = logging.getLogger(__name__)


class NotificationService(BaseNotifier):
    """Listens to events and spawns Hermes CLI notifications."""

    def __init__(self) -> None:
        event_service.register(self)
        logger.info("NotificationService registered on EventService")

    async def notify(self, event: dict[str, Any]) -> None:
        """Called by EventService for every emitted event."""
        try:
            await self._handle_event(event)
        except Exception:
            logger.exception("NotificationService failed to handle event %s", event.get("type"))

    async def _handle_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("type", "")

        if event_type == "issue_status_changed" and event.get("new_status") == "Finished":
            await self._notify_issue_finished(event)

        elif event_type == "question_asked":
            await self._notify_question_asked(event)

    async def _notify_issue_finished(self, event: dict[str, Any]) -> None:
        issue_name = event.get("issue_name", "Untitled")
        issue_id = event.get("issue_id", "unknown")
        message = f"Issue {issue_name} completata"
        logger.info(
            "Notifying issue finished: %s (%s)",
            issue_name, issue_id,
        )
        await self._run_hermes_command(message)

    async def _notify_question_asked(self, event: dict[str, Any]) -> None:
        issue_name = event.get("issue_name", "Untitled")
        question = event.get("question", "")
        message = f"L'issue {issue_name} ha bisogno di una risposta: {question}"
        logger.info(
            "Notifying question asked on issue %s: %.80s",
            issue_name, question,
        )
        await self._run_hermes_command(message)

    @staticmethod
    async def _run_hermes_command(message: str) -> None:
        """Spawn ``hermes chat -q <message> --quiet`` in a subprocess.

        The Hermes CLI must be on ``PATH``. Failures are logged but never
        propagated — the caller (EventService) must not be blocked.
        """
        cmd = HermesProvider.build_notification_command(message)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            if proc.returncode != 0:
                logger.warning(
                    "Hermes notification exited with code %d (message: %.80s)",
                    proc.returncode, message,
                )
        except FileNotFoundError:
            logger.warning(
                "Hermes CLI not found on PATH — cannot send notification: %.80s",
                message,
            )
        except Exception:
            logger.exception("Failed to send Hermes notification: %.80s", message)

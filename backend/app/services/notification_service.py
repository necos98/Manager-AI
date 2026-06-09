"""Notification service — sends Telegram notifications via Hermes CLI.

Listens to Manager AI events (via EventService) and spawns a lightweight
``hermes chat -q`` subprocess to deliver notifications on Telegram.
Also writes a dedicated log file (backend/logs/notifications.log).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from app.providers.hermes_provider import HermesProvider
from app.services.event_service import BaseNotifier, event_service

logger = logging.getLogger(__name__)

_NOTIFICATION_LOG_FORMAT = (
    "[%(asctime)s] NOTIFICA | %(event_type)s | Issue: %(issue_name)s"
    " | Progetto: %(project_name)s | Messaggio: %(message)s"
)
_NOTIFICATION_LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"


class NotificationService(BaseNotifier):
    """Listens to events and spawns Hermes CLI notifications."""

    def __init__(self) -> None:
        event_service.register(self)
        self._notification_logger = self._setup_notification_logger()
        logger.info("NotificationService registered on EventService")

    @staticmethod
    def _setup_notification_logger() -> logging.Logger:
        """Configure and return a dedicated file logger for notifications.

        Writes to ``backend/logs/notifications.log`` in append mode.
        Creates the directory if it doesn't exist.
        """
        handler_name = "NotificationFileHandler"
        # Resolve backend/logs/ relative to this file's location
        dir_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
        )
        os.makedirs(dir_path, exist_ok=True)
        log_path = os.path.join(dir_path, "notifications.log")

        notification_logger = logging.getLogger("NotificationFileLogger")

        # Avoid adding duplicate handlers on re-registration (e.g. tests)
        if not any(
            h.get_name() == handler_name for h in notification_logger.handlers
        ):
            handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
            handler.set_name(handler_name)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                fmt=_NOTIFICATION_LOG_FORMAT,
                datefmt=_NOTIFICATION_LOG_DATE_FMT,
            )
            handler.setFormatter(formatter)
            notification_logger.addHandler(handler)
            notification_logger.setLevel(logging.INFO)
            # Prevent propagation to root logger (we only want the file)
            notification_logger.propagate = False

        return notification_logger

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
        project_name = event.get("project_name", "")
        issue_name = event.get("issue_name", "Untitled")
        description = event.get("description") or ""
        recap = event.get("recap") or ""

        message_parts = []
        if project_name:
            message_parts.append(f"✅ Issue completata — {project_name}")
        else:
            message_parts.append("✅ Issue completata")
        message_parts.append(f"📌 {issue_name}")
        if description:
            desc_short = description.replace("\n", " ").strip()[:120]
            message_parts.append(f"📝 {desc_short}")
        if recap:
            recap_short = recap.replace("\n", " ").strip()[:120]
            message_parts.append(f"💬 {recap_short}")

        hermes_message = "\n".join(message_parts)

        # Write to dedicated notification log
        self._notification_logger.info(
            hermes_message[:200],
            extra={
                "event_type": "issue_finished",
                "issue_name": issue_name or "Untitled",
                "project_name": project_name or "N/A",
            },
        )

        logger.info(
            "Notifying issue finished: %s (%s) — %s",
            issue_name, event.get("issue_id", "unknown"), project_name,
        )
        await self._run_hermes_command(hermes_message)

    async def _notify_question_asked(self, event: dict[str, Any]) -> None:
        project_name = event.get("project_name", "")
        issue_name = event.get("issue_name", "Untitled")
        question = event.get("question", "")

        message_parts = []
        if project_name:
            message_parts.append(f"❓ Domanda in attesa — {project_name}")
        else:
            message_parts.append("❓ Domanda in attesa")
        message_parts.append(f"📌 {issue_name}")
        if question:
            q_short = question.replace("\n", " ").strip()[:200]
            message_parts.append(f"💬 {q_short}")

        hermes_message = "\n".join(message_parts)

        # Write to dedicated notification log
        self._notification_logger.info(
            hermes_message[:200],
            extra={
                "event_type": "question_asked",
                "issue_name": issue_name or "Untitled",
                "project_name": project_name or "N/A",
            },
        )

        logger.info(
            "Notifying question asked on issue %s: %.80s",
            issue_name, question,
        )
        await self._run_hermes_command(hermes_message)

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

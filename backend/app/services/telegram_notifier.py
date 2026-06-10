"""Telegram notifier — sends notifications via Telegram Bot API directly.

Listens to Manager AI events (via EventService) and sends them to
Telegram using ``TelegramService`` (httpx → Bot API), replacing the
Hermes CLI subprocess approach.

If Telegram is not configured (no token/chat_id), the notifier is a
silent no-op — no crashes, no errors.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.event_service import BaseNotifier, event_service
from app.services.telegram_service import telegram_service

logger = logging.getLogger(__name__)


class TelegramNotifier(BaseNotifier):
    """Listens to events and sends Telegram notifications via Bot API."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
        notifications_enabled: bool | None = None,
    ) -> None:
        event_service.register(self)

        # Apply DB-based configuration if provided
        if bot_token is not None or chat_id is not None or notifications_enabled is not None:
            telegram_service.configure(
                bot_token=bot_token or "",
                chat_id=chat_id or "",
                enabled=bool(notifications_enabled) if notifications_enabled is not None else False,
            )

        if telegram_service.is_configured():
            logger.info("TelegramNotifier registered on EventService (direct Bot API)")
        else:
            logger.info(
                "TelegramNotifier registered but NOT configured — "
                "set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env "
                "or configure via Settings UI"
            )

    async def notify(self, event: dict[str, Any]) -> None:
        """Called by EventService for every emitted event."""
        if not telegram_service.is_configured():
            return

        try:
            await self._handle_event(event)
        except Exception:
            logger.exception(
                "TelegramNotifier failed to handle event %s", event.get("type")
            )

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

        message = "\n".join(message_parts)

        logger.info(
            "Telegram notify issue finished: %s (%s) — %s",
            issue_name, event.get("issue_id", "unknown"), project_name,
        )
        await telegram_service.send_message(message)

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

        message = "\n".join(message_parts)

        logger.info(
            "Telegram notify question asked on issue %s: %.80s",
            issue_name, question,
        )
        await telegram_service.send_message(message)

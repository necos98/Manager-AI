"""Telegram notification service — direct Bot API calls via httpx.

Replaces the Hermes CLI subprocess approach with direct HTTPS calls
to the Telegram Bot API. More reliable, traceable, and faster.

Usage:
    from app.services.telegram_service import telegram_service

    if telegram_service.is_configured():
        await telegram_service.send_message("Hello from Manager AI!")

Design:
- Singleton pattern (module-level ``telegram_service`` instance)
- Uses httpx.AsyncClient with connection pooling
- Automatic retry (1 extra attempt after 2s on network errors)
- Rate limiting: max 20 messages/second (Telegram Bot API limit)
- Structured logging with chat_id, message_id, success/failure
- Never propagates exceptions — callers must not block on notifications
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Sentinel value to detect when configure() was never called
_UNSET = object()

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"
_MAX_RETRIES = 1        # one retry after a failure
_RETRY_DELAY_S = 2.0     # wait 2s before retrying
_REQUEST_TIMEOUT_S = 15.0
_RATE_LIMIT_PER_SECOND = 20


class TelegramService:
    """Sends messages to Telegram via the Bot API.

    Configured via ``TELEGRAM_BOT_TOKEN`` and ``TELEGRAM_CHAT_ID``
    in ``.env`` (loaded by pydantic-settings into ``app.config.settings``).
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._last_message_time: float = 0.0
        # Values from env (fallback)
        self._token: str = settings.telegram_bot_token
        self._default_chat_id: str = settings.telegram_chat_id
        self._notifications_enabled: bool = bool(settings.telegram_bot_token)
        # Track whether configure() was called to distinguish DB vs env config
        self._configured: bool = False

    # ── Public API ────────────────────────────────────────────────────────

    def is_configured(self) -> bool:
        """Whether the service has enough config to send messages."""
        return bool(self._token and self._default_chat_id and self._notifications_enabled)

    def configure(
        self,
        *,
        bot_token: str = "",
        chat_id: str = "",
        enabled: bool = False,
    ) -> None:
        """Override configuration from DB settings.

        Only sets non-empty values so env vars remain the fallback when
        the DB value is empty.  When ``bot_token`` is non-empty but
        ``chat_id`` is empty, only the token is replaced.
        """
        if bot_token:
            self._token = bot_token
        if chat_id:
            self._default_chat_id = chat_id
        self._notifications_enabled = enabled
        self._configured = True

    async def send_message(
        self,
        text: str,
        chat_id: str | None = None,
    ) -> bool:
        """Send a text message to a Telegram chat.

        Args:
            text: Message text (supports HTML parse_mode).
            chat_id: Target chat. Falls back to ``TELEGRAM_CHAT_ID``.

        Returns:
            True if the message was sent successfully, False otherwise.
        """
        if not self.is_configured():
            logger.debug("TelegramService not configured — skipping message")
            return False

        cid = chat_id or self._default_chat_id
        if not cid:
            logger.warning("No chat_id provided and TELEGRAM_CHAT_ID is empty")
            return False

        return await self._send_with_retry(cid, text)

    # ── Helpers ───────────────────────────────────────────────────────────

    async def _send_with_retry(self, chat_id: str, text: str) -> bool:
        """Send message with optional retry on network errors."""
        for attempt in range(1 + _MAX_RETRIES):
            try:
                result = await self._do_send(chat_id, text)
                if result:
                    return True
                # Non-retriable error (e.g. invalid token / blocked bot)
                logger.warning(
                    "Telegram API error sending to chat %s (attempt %d/%d)",
                    chat_id, attempt + 1, 1 + _MAX_RETRIES,
                )
                return False
            except httpx.TimeoutException:
                logger.warning(
                    "Telegram API timeout sending to chat %s (attempt %d/%d)",
                    chat_id, attempt + 1, 1 + _MAX_RETRIES,
                )
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "Telegram API HTTP %d sending to chat %s (attempt %d/%d): %.80s",
                    exc.response.status_code, chat_id,
                    attempt + 1, 1 + _MAX_RETRIES, exc.response.text[:80],
                )
                # 4xx errors are not retriable
                if 400 <= exc.response.status_code < 500:
                    return False
            except httpx.RequestError as exc:
                logger.warning(
                    "Telegram API network error sending to chat %s (attempt %d/%d): %s",
                    chat_id, attempt + 1, 1 + _MAX_RETRIES, exc,
                )

            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAY_S)

        return False

    async def _enforce_rate_limit(self) -> None:
        """Ensure we don't exceed 20 messages/second."""
        now = time.monotonic()
        elapsed = now - self._last_message_time
        min_interval = 1.0 / _RATE_LIMIT_PER_SECOND
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_message_time = time.monotonic()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_S)
        return self._client

    async def _do_send(self, chat_id: str, text: str) -> bool:
        """Perform the actual API call to Telegram."""
        await self._enforce_rate_limit()

        url = TELEGRAM_API_BASE.format(
            token=self._token,
            method="sendMessage",
        )
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        client = self._get_client()
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        if data.get("ok"):
            msg_id = (
                data.get("result", {}).get("message_id", "?")
                if isinstance(data.get("result"), dict) else "?"
            )
            logger.info(
                "Telegram message sent | chat=%s | message_id=%s | len=%d",
                chat_id, msg_id, len(text),
            )
            return True

        logger.warning(
            "Telegram API returned ok=false | chat=%s | description=%.80s",
            chat_id, data.get("description", ""),
        )
        return False

    async def close(self) -> None:
        """Close the underlying httpx client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Module-level singleton
telegram_service = TelegramService()

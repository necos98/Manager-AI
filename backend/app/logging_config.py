"""Centralized error logging configuration.

Provides:
- ``ErrorFileHandler`` — ``logging.Handler`` that writes one file per error
- ``ErrorLoggerService`` — explicit service for rich-context errors
- ``configure_error_logging()`` — one-shot application init
"""

from __future__ import annotations

import contextvars
import logging
import os
import sys
import traceback as tb_module
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.error_format import format_error_log

# Async-safe request context propagation.
# Set by ErrorLoggerService.set_request_context() before logging,
# read by ErrorFileHandler.emit() during formatting.
_request_context: contextvars.ContextVar[dict[str, Any] | None] = (
    contextvars.ContextVar("error_request_context", default=None)
)


class _ClientDisconnectFilter(logging.Filter):
    """Suppress log records whose exception is ClientDisconnect."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info:
            exc_type = record.exc_info[0]
            if exc_type is not None and exc_type.__name__ == "ClientDisconnect":
                return False
        return True


class ErrorFileHandler(logging.Handler):
    """Logging handler that writes one plain-text file per error.

    Auto-captures all ``logger.error()`` and ``logger.exception()`` calls
    from the root logger.  Each error gets its own file in the configured
    log directory.
    """

    def __init__(self, log_dir: str = "backend/logs/", level: int = logging.ERROR):
        super().__init__(level=level)
        self._log_dir = log_dir
        self.addFilter(_ClientDisconnectFilter())

    # ------------------------------------------------------------------
    # File path helpers
    # ------------------------------------------------------------------

    def _ensure_dir(self) -> Path:
        path = Path(self._log_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _unique_path(directory: Path, timestamp: str) -> Path:
        """Return a non-existent file path with optional random suffix."""
        base = directory / f"error_{timestamp}"
        path = base.with_suffix(".log")
        if not path.exists():
            return path
        for _ in range(100):
            suffix = os.urandom(3).hex()
            path = directory / f"error_{timestamp}_{suffix}.log"
            if not path.exists():
                return path
        # Extremely unlikely — fallback to PID
        return directory / f"error_{timestamp}_{os.getpid()}.log"

    # ------------------------------------------------------------------
    # Handler interface
    # ------------------------------------------------------------------

    def emit(self, record: logging.LogRecord) -> None:
        """Write a single error log file for the given record."""
        # Ensure directory exists
        try:
            directory = self._ensure_dir()
        except OSError:
            self.handleError(record)
            return

        # Timestamps
        now_utc = datetime.fromtimestamp(record.created, tz=timezone.utc)
        timestamp_file = now_utc.strftime("%Y%m%d_%H%M%S")
        timestamp_iso = now_utc.isoformat()

        # Error classification
        message = record.getMessage()
        exc_type_name = "Unknown"

        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            if exc_type is not None:
                exc_type_name = exc_type.__name__
            if exc_value is not None:
                message = str(exc_value)

        # Traceback
        tb_str = ""
        if record.exc_info:
            tb_str = "".join(tb_module.format_exception(*record.exc_info))
        elif record.exc_text:
            tb_str = record.exc_text

        # Request context (set via ErrorLoggerService / contextvars)
        req_ctx = _request_context.get()

        content = format_error_log(
            exc_type_name=exc_type_name,
            message=message,
            pathname=record.pathname,
            lineno=record.lineno,
            timestamp=timestamp_iso,
            traceback_str=tb_str,
            request_context=req_ctx,
            metadata={
                "PID": record.process,
                "Logger": record.name,
                "Process": record.processName,
            },
        )

        path = self._unique_path(directory, timestamp_file)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError:
            self.handleError(record)


class ErrorLoggerService:
    """Explicit logging for errors that need rich context.

    Use in catch blocks where you want to attach request context,
    pipeline metadata, or other structured data to the error log.
    """

    @staticmethod
    def log_exception(
        exc: Exception,
        request_context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an exception with optional request context and metadata.

        The exception's traceback is captured even when called outside
        an ``except`` block (via explicit ``exc_info`` tuple).
        """
        if request_context is not None:
            _request_context.set(request_context)
        try:
            logger = logging.getLogger("app.error_service")
            logger.exception(
                "%s: %s",
                type(exc).__name__,
                str(exc),
                exc_info=(type(exc), exc, exc.__traceback__),
            )
        finally:
            if request_context is not None:
                _request_context.set(None)

    @staticmethod
    def set_request_context(ctx: dict[str, Any] | None) -> None:
        """Set request context for the current async context.

        The context is picked up by ``ErrorFileHandler`` during formatting.
        """
        if ctx is not None:
            _request_context.set(ctx)
        else:
            _request_context.set(None)

    @staticmethod
    def clear_request_context() -> None:
        """Clear request context for the current async context."""
        _request_context.set(None)


# ------------------------------------------------------------------
# One-shot application init
# ------------------------------------------------------------------

_initialized: bool = False


def configure_error_logging(log_dir: str = "backend/logs/") -> ErrorFileHandler:
    """Initialize the error logging system.

    Call **once** at application startup, after the asyncio event loop
    is running.  This function:

    * Creates an ``ErrorFileHandler`` and attaches it to the root logger
      at ERROR level.
    * Installs ``sys.excepthook`` for uncaught synchronous exceptions.
    * Does **not** touch the asyncio exception handler — the application
      is responsible for its own asyncio handler (e.g. Windows accept
      noise suppression).

    Returns the ``ErrorFileHandler`` instance.
    """
    global _initialized
    if _initialized:
        logging.getLogger(__name__).warning(
            "configure_error_logging() called more than once"
        )
        return ErrorFileHandler(log_dir=log_dir)

    _initialized = True

    handler = ErrorFileHandler(log_dir=log_dir)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    # -- sys.excepthook for uncaught sync exceptions ------------------
    def _excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: Any,
    ) -> None:
        if exc_type is KeyboardInterrupt:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger = logging.getLogger("excepthook")
        logger.exception(
            "Uncaught exception: %s: %s",
            exc_type.__name__,
            str(exc_value),
            exc_info=(exc_type, exc_value, exc_tb),
        )

    sys.excepthook = _excepthook

    return handler

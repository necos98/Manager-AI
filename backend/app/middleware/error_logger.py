"""Middleware that logs unhandled exceptions to a daily rotating file."""
from __future__ import annotations

import logging
import traceback
import json
from datetime import datetime, timezone
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"

logger = logging.getLogger(__name__)


def _log_file_path() -> Path:
    """Return the path for today's log file, e.g. logs/2026-05-27.log."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return LOGS_DIR / f"{today}.log"


def _write_error(entry: dict) -> None:
    """Append a JSON error entry to today's log file."""
    try:
        path = _log_file_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")
    except OSError:
        logger.exception("Failed to write error log entry")


class ErrorLoggerMiddleware(BaseHTTPMiddleware):
    """Catch-all middleware that logs any unhandled exception to a daily log file.

    After logging, the exception is re-raised so FastAPI's normal error-handling
    chain (including the AppError handler) still runs.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": request.method,
                "path": request.url.path,
                "query_string": str(request.query_params),
                "client": request.client.host if request.client else None,
                "error_type": None,
                "error_message": None,
                "traceback": None,
            }
            try:
                raise  # re-raise to capture the full traceback
            except Exception:
                import sys
                exc_type, exc_value, _ = sys.exc_info()
                entry["error_type"] = exc_type.__name__ if exc_type else "Unknown"
                entry["error_message"] = str(exc_value) if exc_value else ""
                entry["traceback"] = traceback.format_exc()

            _write_error(entry)
            raise  # re-raise so FastAPI still returns the HTTP 500 response

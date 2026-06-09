"""Middleware that logs unhandled exceptions via ErrorLoggerService."""
from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request, ClientDisconnect
from starlette.responses import Response

from app.logging_config import ErrorLoggerService

logger = logging.getLogger(__name__)


class ErrorLoggerMiddleware(BaseHTTPMiddleware):
    """Catch-all middleware that logs unhandled exceptions to per-error files.

    After logging, the exception is re-raised so FastAPI's normal error-handling
    chain (including the AppError handler) still runs.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except ClientDisconnect:
            logger.debug("Client disconnected during request to %s", request.url.path)
            return Response(status_code=499)
        except Exception as exc:
            request_context = {
                "Method": request.method,
                "Path": request.url.path,
                "Query": str(request.query_params),
                "Client": request.client.host if request.client else None,
            }
            ErrorLoggerService.log_exception(exc, request_context=request_context)
            raise

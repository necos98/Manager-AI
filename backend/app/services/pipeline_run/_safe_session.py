"""Safe database session helpers for the long-running pipeline background task."""

import logging

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def safe_flush(session: AsyncSession) -> None:
    """Flush with automatic rollback on failure."""
    try:
        await session.flush()
    except Exception:
        logger.warning("safe_flush: flush failed, rolling back", exc_info=True)
        await session.rollback()
        await session.flush()


async def safe_commit(session: AsyncSession) -> None:
    """Commit with automatic rollback on failure.

    Re-raises IntegrityError and OperationalError immediately (they won't
    recover from rollback) instead of silently swallowing them.
    """
    try:
        await session.commit()
    except (IntegrityError, OperationalError):
        logger.error("safe_commit: non-recoverable error", exc_info=True)
        raise
    except Exception:
        logger.warning("safe_commit: commit failed, rolling back", exc_info=True)
        await session.rollback()
        await session.commit()

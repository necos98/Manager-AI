from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pipeline_log import PipelineLog

logger = logging.getLogger(__name__)


class PipelineLogService:
    """Structured logging for pipeline runs.

    Logs every state transition, exception, and system event during
    pipeline execution. Writes are non-blocking (flush, not commit) so the
    caller's transaction owns the commit.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        pipeline_run_id: str,
        level: str = "INFO",
        source: str = "",
        message: str = "",
        step_run_id: Optional[str] = None,
        details: dict | None = None,
    ) -> PipelineLog:
        """Write a log entry.  Flushed but NOT committed — caller owns commit."""
        entry = PipelineLog(
            pipeline_run_id=pipeline_run_id,
            step_run_id=step_run_id,
            level=level,
            source=source,
            message=message,
            details=json.dumps(details or {}),
        )
        self.session.add(entry)
        try:
            await self.session.flush()
        except Exception:
            logger.warning("PipelineLog flush failed — logging skipped", exc_info=True)
            await self.session.rollback()
        return entry

    async def log_exception(
        self,
        pipeline_run_id: str,
        source: str,
        message: str,
        exception: Exception,
        step_run_id: Optional[str] = None,
    ) -> PipelineLog:
        """Convenience — log an ERROR entry with exception details."""
        details = {
            "error_type": type(exception).__name__,
            "error_message": str(exception),
        }
        return await self.log(
            pipeline_run_id=pipeline_run_id,
            level="ERROR",
            source=source,
            message=message,
            step_run_id=step_run_id,
            details=details,
        )

    async def get_logs_for_run(
        self,
        pipeline_run_id: str,
        limit: int = 200,
        offset: int = 0,
        level: Optional[str] = None,
    ) -> list[dict]:
        query = (
            select(PipelineLog)
            .where(PipelineLog.pipeline_run_id == pipeline_run_id)
            .order_by(PipelineLog.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        if level:
            query = query.where(PipelineLog.level == level)

        result = await self.session.execute(query)
        logs = result.scalars().all()
        return [_log_to_dict(log) for log in logs]

    async def get_logs_for_issue(
        self,
        run_ids: list[str],
        limit: int = 500,
        offset: int = 0,
        level: Optional[str] = None,
    ) -> list[dict]:
        """Get logs for all pipeline runs of an issue, ordered by time."""
        if not run_ids:
            return []
        query = (
            select(PipelineLog)
            .where(PipelineLog.pipeline_run_id.in_(run_ids))
            .order_by(PipelineLog.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        if level:
            query = query.where(PipelineLog.level == level)

        result = await self.session.execute(query)
        logs = result.scalars().all()
        return [_log_to_dict(log) for log in logs]

    async def count_logs_for_run(
        self,
        pipeline_run_id: str,
        level: Optional[str] = None,
    ) -> int:
        from sqlalchemy import func as sa_func

        query = select(sa_func.count()).select_from(PipelineLog).where(
            PipelineLog.pipeline_run_id == pipeline_run_id
        )
        if level:
            query = query.where(PipelineLog.level == level)
        result = await self.session.execute(query)
        return result.scalar() or 0


def _log_to_dict(log: PipelineLog) -> dict:
    return {
        "id": log.uuid,
        "pipeline_run_id": str(log.pipeline_run_id),
        "step_run_id": str(log.step_run_id) if log.step_run_id else None,
        "level": log.level,
        "source": log.source,
        "message": log.message,
        "details": log.get_details(),
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }

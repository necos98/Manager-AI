from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog


class ActivityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        project_id: str,
        issue_id: Optional[str],
        event_type: str,
        details: dict | None = None,
    ) -> ActivityLog:
        entry = ActivityLog(
            project_id=project_id,
            issue_id=issue_id,
            event_type=event_type,
            details=json.dumps(details or {}),
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_for_project(
        self,
        project_id: str,
        issue_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ActivityLog]:
        query = (
            select(ActivityLog)
            .where(ActivityLog.project_id == project_id)
            .order_by(ActivityLog.created_at.desc(), text("rowid DESC"))
            .limit(limit)
            .offset(offset)
        )
        if issue_id is not None:
            query = query.where(ActivityLog.issue_id == issue_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

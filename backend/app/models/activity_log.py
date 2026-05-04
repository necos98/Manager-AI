import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Plain column — no FK. Issues live in .manager_ai/ not in DB; log rows must
    # survive issue deletion as audit trail.
    issue_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    def get_details(self) -> dict:
        try:
            return json.loads(self.details)
        except (json.JSONDecodeError, TypeError):
            return {}

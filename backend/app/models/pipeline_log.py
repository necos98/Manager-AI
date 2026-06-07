import json
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._uuid import new_uuid


class PipelineLog(Base):
    __tablename__ = "pipeline_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False, default=new_uuid)
    pipeline_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_run_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("pipeline_step_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    level: Mapped[str] = mapped_column(String(10), nullable=False, default="INFO")
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    def get_details(self) -> dict:
        try:
            return json.loads(self.details)
        except (json.JSONDecodeError, TypeError):
            return {}

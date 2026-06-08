import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PipelineEventRule(Base):
    __tablename__ = "pipeline_event_rules"
    __table_args__ = (
        UniqueConstraint(
            "pipeline_id", "event_type", "source_step_id",
            name="uq_pipeline_event_rule",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    pipeline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_step_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_steps.id"), nullable=False
    )
    target_step_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_steps.id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="redirect"
    )
    action_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    pipeline = relationship("Pipeline", back_populates="event_rules")
    source_step = relationship("PipelineStep", foreign_keys=[source_step_id])
    target_step = relationship("PipelineStep", foreign_keys=[target_step_id])

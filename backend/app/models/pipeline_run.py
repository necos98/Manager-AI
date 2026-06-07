import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PipelineRunStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    WAITING_FOR_STEP = "WAITING_FOR_STEP"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineStepRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), nullable=False, index=True)
    issue_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[PipelineRunStatus] = mapped_column(Enum(PipelineRunStatus), nullable=False, default=PipelineRunStatus.RUNNING)
    current_step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orchestrated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    pipeline = relationship("Pipeline", back_populates="runs")
    step_runs = relationship("PipelineStepRun", back_populates="pipeline_run", cascade="all, delete-orphan")
    messages = relationship("PipelineMessage", back_populates="pipeline_run", cascade="all, delete-orphan")


class PipelineStepRun(Base):
    __tablename__ = "pipeline_step_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_step_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_steps.id"), nullable=False)
    terminal_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[PipelineStepRunStatus] = mapped_column(Enum(PipelineStepRunStatus), nullable=False, default=PipelineStepRunStatus.PENDING)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    pipeline_run = relationship("PipelineRun", back_populates="step_runs")
    pipeline_step = relationship("PipelineStep", back_populates="step_runs")


class PipelineMessage(Base):
    __tablename__ = "pipeline_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    pipeline_run = relationship("PipelineRun", back_populates="messages")

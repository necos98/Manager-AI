import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PipelineRunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class AgentStepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    steps: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False, default="issue_accepted")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), nullable=False)
    issue_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("issues.id"), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[PipelineRunStatus] = mapped_column(
        Enum(PipelineRunStatus), nullable=False, default=PipelineRunStatus.RUNNING
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AgentStepRun(Base):
    __tablename__ = "agent_step_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_runs.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_role: Mapped[str] = mapped_column(String(100), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AgentStepStatus] = mapped_column(
        Enum(AgentStepStatus), nullable=False, default=AgentStepStatus.PENDING
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

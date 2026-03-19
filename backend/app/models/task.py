import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskStatus(str, enum.Enum):
    NEW = "New"
    REASONING = "Reasoning"
    PLANNED = "Planned"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    FINISHED = "Finished"
    CANCELED = "Canceled"


# Valid state transitions: (from_status, to_status)
VALID_TRANSITIONS = {
    (TaskStatus.NEW, TaskStatus.PLANNED),
    (TaskStatus.DECLINED, TaskStatus.PLANNED),
    (TaskStatus.REASONING, TaskStatus.PLANNED),
    (TaskStatus.PLANNED, TaskStatus.ACCEPTED),
    (TaskStatus.PLANNED, TaskStatus.DECLINED),
    (TaskStatus.ACCEPTED, TaskStatus.FINISHED),
}
# Any → Canceled is always valid (handled in code)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False, default=TaskStatus.NEW)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recap: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decline_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")

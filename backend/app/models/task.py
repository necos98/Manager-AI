import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskStatus(str, enum.Enum):
    NEW = "New"
    PLANNED = "Planned"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    FINISHED = "Finished"
    CANCELED = "Canceled"


# Valid state transitions: (from_status, to_status)
VALID_TRANSITIONS = {
    (TaskStatus.NEW, TaskStatus.PLANNED),
    (TaskStatus.DECLINED, TaskStatus.PLANNED),
    (TaskStatus.PLANNED, TaskStatus.ACCEPTED),
    (TaskStatus.PLANNED, TaskStatus.DECLINED),
    (TaskStatus.ACCEPTED, TaskStatus.FINISHED),
}
# Any → Canceled is always valid (handled in code)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False, default=TaskStatus.NEW)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    recap: Mapped[str | None] = mapped_column(Text, nullable=True)
    decline_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_embedding = Column(Vector(1536), nullable=True)
    plan_embedding = Column(Vector(1536), nullable=True)
    recap_embedding = Column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")

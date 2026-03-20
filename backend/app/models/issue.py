import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IssueStatus(str, enum.Enum):
    NEW = "New"
    REASONING = "Reasoning"
    PLANNED = "Planned"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    FINISHED = "Finished"
    CANCELED = "Canceled"


VALID_TRANSITIONS = {
    (IssueStatus.REASONING, IssueStatus.PLANNED),
    (IssueStatus.PLANNED, IssueStatus.ACCEPTED),
    (IssueStatus.PLANNED, IssueStatus.DECLINED),
    (IssueStatus.ACCEPTED, IssueStatus.FINISHED),
}


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IssueStatus] = mapped_column(Enum(IssueStatus), nullable=False, default=IssueStatus.NEW)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recap: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decline_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="issues")
    tasks = relationship("Task", back_populates="issue", cascade="all, delete-orphan", order_by="Task.order")

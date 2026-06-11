import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QueueEntryStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    STALLED = "stalled"


class QueueEntry(Base):
    """Registro persistente delle issue accodate per il dispacciamento FIFO.

    Ogni entry rappresenta un'operazione di accodamento. Il registro
    sopravvive ai cambi di status dell'issue, permettendo tracciabilità
    completa del ciclo di vita della coda.
    """

    __tablename__ = "queue_entries"

    __table_args__ = (
        UniqueConstraint("project_id", "order", name="uq_queue_entries_project_order"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    issue_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True,
    )
    project_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True,
    )
    status: Mapped[QueueEntryStatus] = mapped_column(
        Enum(QueueEntryStatus), nullable=False,
        default=QueueEntryStatus.PENDING,
    )
    order: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(),
    )
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    last_terminal_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True,
    )
    status_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
    )

import uuid
from datetime import datetime

from app.utils.datetime import naive_utc_now
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return naive_utc_now()


class IssueFeedback(Base):
    __tablename__ = "issue_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    issue = relationship("Issue", back_populates="feedback")

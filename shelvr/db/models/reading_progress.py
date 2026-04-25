"""ReadingProgress model — per-user reading position.

The pre-v1 spec also tracked a ``device_id`` so the same user could resume on
their phone vs. their laptop separately. v1 ships single-position per user
to keep the data model simple; per-device tracking can layer on later by
relaxing the (book_id, user_id) UNIQUE constraint.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import TIMESTAMP, Float, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from shelvr.db.base import Base


class ReadingProgress(Base):
    """Where a user left off in a given book."""

    __tablename__ = "reading_progress"
    __table_args__ = (UniqueConstraint("book_id", "user_id", name="uq_reading_progress_book_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

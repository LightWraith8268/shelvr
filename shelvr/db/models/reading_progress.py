"""ReadingProgress model -- per-device reading position."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import TIMESTAMP, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shelvr.db.base import Base


class ReadingProgress(Base):
    """Reading position for one book on one device.

    ``locator`` is a Readium-compatible JSON blob (CFI or page+offset).
    """

    __tablename__ = "reading_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

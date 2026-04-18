"""Format model -- a concrete ebook file on disk."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from shelvr.db.base import Base


class Format(Base):
    """A concrete file belonging to a book."""

    __tablename__ = "formats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(2000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    date_added: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.current_timestamp()
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False, server_default="import")

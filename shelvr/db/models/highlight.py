"""Highlight model — per-user text-range annotations within a book."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shelvr.db.base import Base


class Highlight(Base):
    """A user's saved text range with an optional note.

    ``locator_range`` carries the reader-defined range identifier (an EPUB CFI
    range like ``epubcfi(/6/4!/4/2/1:0,/4/2/1:50)`` for epub.js). ``text``
    caches the selection so the sidebar can render a preview without
    re-resolving the range. ``color`` is one of yellow/green/blue/pink.
    """

    __tablename__ = "highlights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    locator_range: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    color: Mapped[str] = mapped_column(Text, nullable=False, default="yellow")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

"""Identifier model -- external IDs per book (ISBN, Goodreads, Open Library, etc.)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shelvr.db.base import Base


class Identifier(Base):
    """An external identifier for a book."""

    __tablename__ = "identifiers"
    __table_args__ = (UniqueConstraint("book_id", "scheme", "value", name="uq_identifier"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    scheme: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)

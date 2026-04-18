"""Author model."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from shelvr.db.base import Base


class Author(Base):
    """A book author."""

    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_name: Mapped[str | None] = mapped_column(String(500), nullable=True)

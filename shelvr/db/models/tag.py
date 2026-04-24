"""Tag model."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from shelvr.db.base import Base


class Tag(Base):
    """A user-defined book tag."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)

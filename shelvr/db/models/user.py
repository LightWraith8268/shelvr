"""User model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from shelvr.db.base import Base


class User(Base):
    """A Shelvr account. Roles: 'admin' or 'reader'."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="reader")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.current_timestamp()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)

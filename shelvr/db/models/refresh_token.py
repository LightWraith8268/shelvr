"""Refresh token model — DB-backed so tokens are revocable."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from shelvr.db.base import Base


class RefreshToken(Base):
    """One row per issued refresh token. Lookup by JWT ``jti`` claim."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.current_timestamp()
    )
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

"""Device model -- one per client (phone, tablet, web session)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from shelvr.db.base import Base


class Device(Base):
    """A registered client device."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    push_token: Mapped[str | None] = mapped_column(String(500), nullable=True)

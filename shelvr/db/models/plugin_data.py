"""PluginData model -- per-plugin key-value storage."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shelvr.db.base import Base


class PluginData(Base):
    """Plugin-scoped KV store."""

    __tablename__ = "plugin_data"
    __table_args__ = (UniqueConstraint("plugin_id", "key", name="uq_plugin_data"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plugin_id: Mapped[str] = mapped_column(String(200), nullable=False)
    key: Mapped[str] = mapped_column(String(500), nullable=False)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)

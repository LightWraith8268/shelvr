"""SQLAlchemy declarative base and async engine factory."""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Use a consistent naming convention so Alembic autogenerate produces stable names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shelvr's declarative base."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_engine(database_url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine with SQLite WAL mode when applicable.

    For in-memory SQLite URLs (containing ``:memory:``), uses StaticPool and
    disables ``check_same_thread`` so the single connection is reused across the
    engine's lifetime — otherwise each new connection would open a fresh empty
    in-memory database and anything we created wouldn't be visible.
    """
    connect_args: dict[str, object] = {}
    engine_kwargs: dict[str, object] = {"future": True}
    if database_url.startswith("sqlite"):
        # Allow connections from any thread; SQLAlchemy's pooling handles isolation.
        connect_args["check_same_thread"] = False
        if ":memory:" in database_url:
            from sqlalchemy.pool import StaticPool

            engine_kwargs["poolclass"] = StaticPool
    return create_async_engine(
        database_url,
        connect_args=connect_args,
        **engine_kwargs,
    )

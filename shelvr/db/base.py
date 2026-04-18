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
    """Create an async SQLAlchemy engine with SQLite WAL mode when applicable."""
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        # Allow connections from any thread; SQLAlchemy's pooling handles isolation.
        connect_args["check_same_thread"] = False
    engine = create_async_engine(
        database_url,
        future=True,
        connect_args=connect_args,
    )
    return engine

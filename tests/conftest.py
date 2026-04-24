"""Shared pytest fixtures for the Shelvr test suite."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool


@pytest.fixture
def library_path(tmp_path: Path) -> Path:
    """A clean, empty library directory per test."""
    library = tmp_path / "library"
    library.mkdir()
    return library


@pytest.fixture
def jwt_secret() -> str:
    """Stable JWT secret for tests."""
    return "test-secret-not-for-production"


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch, library_path: Path, jwt_secret: str) -> object:
    """Load a Settings instance seeded with test values."""
    from shelvr.config import load_settings

    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(library_path))
    monkeypatch.setenv("SHELVR_JWT_SECRET", jwt_secret)
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    return load_settings(config_file=None)


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Per-test in-memory async SQLite engine with all tables created."""
    from shelvr.db import models  # noqa: F401  ensure all models register with metadata
    from shelvr.db.base import Base

    e = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield e
    finally:
        await e.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test async session bound to the in-memory engine."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s

"""Shared FastAPI dependency providers."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shelvr.config import Settings
from shelvr.repositories.books import BookRepository


def get_settings(request: Request) -> Settings:
    """Return the Settings instance stashed on app.state."""
    return request.app.state.settings  # type: ignore[no-any-return]


def get_session_factory(
    request: Request,
) -> async_sessionmaker[AsyncSession]:
    """Return the async_sessionmaker stashed on app.state."""
    return request.app.state.session_factory  # type: ignore[no-any-return]


async def get_session(
    factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a session per request."""
    async with factory() as session:
        yield session


async def get_book_repo(
    session: AsyncSession = Depends(get_session),
) -> BookRepository:
    """Construct a BookRepository bound to the request's session."""
    return BookRepository(session)

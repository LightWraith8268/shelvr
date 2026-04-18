"""Tests for Shelvr SQLAlchemy models."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_author_create(session: AsyncSession) -> None:
    """An author can be created and retrieved with name + sort_name."""
    from shelvr.db.models import Author

    author = Author(name="Ursula K. Le Guin", sort_name="Le Guin, Ursula K.")
    session.add(author)
    await session.flush()

    assert author.id is not None
    assert author.name == "Ursula K. Le Guin"
    assert author.sort_name == "Le Guin, Ursula K."


@pytest.mark.asyncio
async def test_series_create(session: AsyncSession) -> None:
    """A series can be created with name + sort_name + description."""
    from shelvr.db.models import Series

    series = Series(
        name="Earthsea",
        sort_name="Earthsea",
        description="Fantasy series by Ursula K. Le Guin.",
    )
    session.add(series)
    await session.flush()

    assert series.id is not None
    assert series.name == "Earthsea"

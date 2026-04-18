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

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


@pytest.mark.asyncio
async def test_tag_create(session: AsyncSession) -> None:
    """A tag can be created with name + optional color."""
    from shelvr.db.models import Tag

    tag = Tag(name="science-fiction", color="#4287f5")
    session.add(tag)
    await session.flush()

    assert tag.id is not None
    assert tag.name == "science-fiction"
    assert tag.color == "#4287f5"


@pytest.mark.asyncio
async def test_book_create_minimal(session: AsyncSession) -> None:
    """A book can be created with just a title."""
    from shelvr.db.models import Book

    book = Book(title="A Wizard of Earthsea")
    session.add(book)
    await session.flush()

    assert book.id is not None
    assert book.title == "A Wizard of Earthsea"
    assert book.date_added is not None


@pytest.mark.asyncio
async def test_book_author_relationship(session: AsyncSession) -> None:
    """Books can be linked to authors through the book_authors junction."""
    from shelvr.db.models import Author, Book

    author = Author(name="Ursula K. Le Guin", sort_name="Le Guin, Ursula K.")
    book = Book(title="A Wizard of Earthsea", sort_title="Wizard of Earthsea, A")
    book.authors.append(author)
    session.add(book)
    await session.flush()
    await session.refresh(book)

    assert len(book.authors) == 1
    assert book.authors[0].name == "Ursula K. Le Guin"


@pytest.mark.asyncio
async def test_book_tag_relationship(session: AsyncSession) -> None:
    """Books can be linked to tags."""
    from shelvr.db.models import Book, Tag

    tag = Tag(name="fantasy")
    book = Book(title="A Wizard of Earthsea")
    book.tags.append(tag)
    session.add(book)
    await session.flush()
    await session.refresh(book)

    assert len(book.tags) == 1
    assert book.tags[0].name == "fantasy"

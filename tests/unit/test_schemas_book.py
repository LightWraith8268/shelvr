"""Tests for the book Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError


def test_book_create_minimal() -> None:
    from shelvr.schemas.book import BookCreate

    b = BookCreate(title="A Wizard of Earthsea")
    assert b.title == "A Wizard of Earthsea"
    assert b.authors == []
    assert b.tags == []
    assert b.identifiers == {}


def test_book_create_requires_title() -> None:
    from shelvr.schemas.book import BookCreate

    with pytest.raises(ValidationError):
        BookCreate()  # type: ignore[call-arg]


def test_book_create_full() -> None:
    from shelvr.schemas.book import BookCreate

    b = BookCreate(
        title="Book",
        authors=["Author A", "Author B"],
        series="Series",
        series_index=2.5,
        description="Desc",
        language="en",
        publisher="Pub",
        published_date="2024-01-15",
        isbn="9780123456789",
        tags=["tag1", "tag2"],
        identifiers={"isbn": "9780123456789", "goodreads": "42"},
    )
    assert b.authors == ["Author A", "Author B"]
    assert b.series_index == 2.5
    assert b.identifiers["goodreads"] == "42"


def test_book_read_serialization() -> None:
    from shelvr.schemas.book import AuthorRead, BookRead, FormatRead

    now = datetime(2026, 4, 19, 12, 0, 0)
    b = BookRead(
        id=1,
        title="Book",
        sort_title=None,
        authors=[AuthorRead(id=1, name="Author", sort_name=None)],
        series=None,
        series_index=None,
        description=None,
        language="en",
        publisher=None,
        published_date=None,
        isbn=None,
        rating=None,
        tags=[],
        identifiers={},
        formats=[
            FormatRead(
                id=1,
                format="epub",
                file_path="Author/Book/Book.epub",
                file_size=1000,
                file_hash="a" * 64,
                source="import",
                date_added=now,
            )
        ],
        date_added=now,
        date_modified=now,
        cover_path=None,
    )
    data = b.model_dump()
    assert data["id"] == 1
    assert data["formats"][0]["format"] == "epub"
    assert data["authors"][0]["name"] == "Author"


def test_book_update_is_partial() -> None:
    """BookUpdate allows any subset of fields; title is optional on update."""
    from shelvr.schemas.book import BookUpdate

    b = BookUpdate(rating=8)
    assert b.rating == 8
    assert b.title is None


def test_book_update_rating_range_validation() -> None:
    """BookUpdate.rating must be 0..10."""
    from shelvr.schemas.book import BookUpdate

    BookUpdate(rating=0)
    BookUpdate(rating=10)
    with pytest.raises(ValidationError):
        BookUpdate(rating=-1)
    with pytest.raises(ValidationError):
        BookUpdate(rating=11)


def test_author_read_from_sqlalchemy_orm() -> None:
    """AuthorRead has from_attributes=True so it works with SQLAlchemy instances."""
    from shelvr.schemas.book import AuthorRead

    # Simulate an ORM-like object
    class FakeAuthor:
        id = 7
        name = "Test"
        sort_name = "Test, Author"

    a = AuthorRead.model_validate(FakeAuthor())
    assert a.id == 7
    assert a.name == "Test"

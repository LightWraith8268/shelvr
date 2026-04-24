"""Integration tests for BookRepository."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_repo_create_book_from_metadata_simple(session: AsyncSession) -> None:
    """create_from_metadata persists a minimal book."""
    from shelvr.repositories.books import BookRepository
    from shelvr.schemas.book import BookCreate

    repo = BookRepository(session)
    created_book = await repo.create_from_metadata(
        BookCreate(title="Test Book", authors=["Test Author"]),
        cover_path=None,
    )
    await session.flush()
    await session.refresh(created_book, attribute_names=["authors", "tags"])

    assert created_book.id is not None
    assert created_book.title == "Test Book"
    assert len(created_book.authors) == 1
    assert created_book.authors[0].name == "Test Author"


@pytest.mark.asyncio
async def test_repo_reuses_existing_author(session: AsyncSession) -> None:
    """Two books by the same author share one Author row."""
    from shelvr.db.models import Author
    from shelvr.repositories.books import BookRepository
    from shelvr.schemas.book import BookCreate

    repo = BookRepository(session)
    first_book = await repo.create_from_metadata(
        BookCreate(title="Book 1", authors=["Shared Author"]), cover_path=None
    )
    second_book = await repo.create_from_metadata(
        BookCreate(title="Book 2", authors=["Shared Author"]), cover_path=None
    )
    await session.flush()
    await session.refresh(first_book, attribute_names=["authors"])
    await session.refresh(second_book, attribute_names=["authors"])

    assert first_book.authors[0].id == second_book.authors[0].id

    author_rows = await session.execute(select(Author).where(Author.name == "Shared Author"))
    assert len(author_rows.scalars().all()) == 1


@pytest.mark.asyncio
async def test_repo_reuses_existing_tag(session: AsyncSession) -> None:
    """Two books tagged 'fantasy' share one Tag row."""
    from shelvr.db.models import Tag
    from shelvr.repositories.books import BookRepository
    from shelvr.schemas.book import BookCreate

    repo = BookRepository(session)
    await repo.create_from_metadata(BookCreate(title="Book 1", tags=["fantasy"]), cover_path=None)
    await repo.create_from_metadata(BookCreate(title="Book 2", tags=["fantasy"]), cover_path=None)
    await session.flush()

    tag_rows = await session.execute(select(Tag).where(Tag.name == "fantasy"))
    assert len(tag_rows.scalars().all()) == 1


@pytest.mark.asyncio
async def test_repo_get_by_hash_returns_none_when_missing(session: AsyncSession) -> None:
    from shelvr.repositories.books import BookRepository

    repo = BookRepository(session)
    missing_book = await repo.get_by_hash("a" * 64)
    assert missing_book is None


@pytest.mark.asyncio
async def test_repo_get_by_hash_finds_book(session: AsyncSession) -> None:
    """get_by_hash returns the book whose Format has the matching hash."""
    from shelvr.db.models import Format
    from shelvr.repositories.books import BookRepository
    from shelvr.schemas.book import BookCreate

    repo = BookRepository(session)
    original_book = await repo.create_from_metadata(
        BookCreate(title="Hashed Book"), cover_path=None
    )
    await session.flush()
    target_hash = "b" * 64
    session.add(
        Format(
            book_id=original_book.id,
            format="epub",
            file_path="path.epub",
            file_size=100,
            file_hash=target_hash,
            source="import",
        )
    )
    await session.flush()

    found_book = await repo.get_by_hash(target_hash)
    assert found_book is not None
    assert found_book.id == original_book.id


@pytest.mark.asyncio
async def test_repo_create_book_with_identifiers(session: AsyncSession) -> None:
    """Identifiers are created alongside the book."""
    from shelvr.db.models import Identifier
    from shelvr.repositories.books import BookRepository
    from shelvr.schemas.book import BookCreate

    repo = BookRepository(session)
    created_book = await repo.create_from_metadata(
        BookCreate(
            title="Book",
            isbn="9780123456789",
            identifiers={"isbn": "9780123456789", "goodreads": "42"},
        ),
        cover_path=None,
    )
    await session.flush()

    identifier_rows = await session.execute(
        select(Identifier).where(Identifier.book_id == created_book.id)
    )
    id_pairs = {
        (identifier.scheme, identifier.value) for identifier in identifier_rows.scalars().all()
    }
    assert ("isbn", "9780123456789") in id_pairs
    assert ("goodreads", "42") in id_pairs


@pytest.mark.asyncio
async def test_repo_add_format_to_book(session: AsyncSession) -> None:
    """add_format attaches a Format record to an existing book."""
    from shelvr.repositories.books import BookRepository
    from shelvr.schemas.book import BookCreate

    repo = BookRepository(session)
    parent_book = await repo.create_from_metadata(BookCreate(title="Book"), cover_path=None)
    await session.flush()

    new_format = await repo.add_format(
        book_id=parent_book.id,
        format="epub",
        file_path="relative/path.epub",
        file_size=1024,
        file_hash="c" * 64,
        source="import",
    )
    await session.flush()

    assert new_format.id is not None
    assert new_format.book_id == parent_book.id
    assert new_format.file_hash == "c" * 64


@pytest.mark.asyncio
async def test_repo_create_book_with_cover_path(session: AsyncSession) -> None:
    """cover_path argument is persisted on the book row."""
    from shelvr.repositories.books import BookRepository
    from shelvr.schemas.book import BookCreate

    repo = BookRepository(session)
    created_book = await repo.create_from_metadata(
        BookCreate(title="Illustrated"),
        cover_path="Author/Title/cover.jpg",
    )
    await session.flush()

    assert created_book.cover_path == "Author/Title/cover.jpg"


@pytest.mark.asyncio
async def test_repo_dedupes_tags_case_insensitively(session: AsyncSession) -> None:
    """Duplicate tag strings (including casefold-equivalent) don't trip the UNIQUE constraint."""
    from shelvr.db.models import Tag
    from shelvr.repositories.books import BookRepository
    from shelvr.schemas.book import BookCreate

    repo = BookRepository(session)
    created_book = await repo.create_from_metadata(
        BookCreate(title="PG Book", tags=["Fiction", "Fiction", "fiction", " FICTION "]),
        cover_path=None,
    )
    await session.flush()
    await session.refresh(created_book, attribute_names=["tags"])

    assert len(created_book.tags) == 1
    assert created_book.tags[0].name == "Fiction"

    tag_rows = await session.execute(select(Tag))
    assert len(tag_rows.scalars().all()) == 1


@pytest.mark.asyncio
async def test_repo_dedupes_authors_case_insensitively(session: AsyncSession) -> None:
    """Duplicate author strings collapse to one link."""
    from shelvr.repositories.books import BookRepository
    from shelvr.schemas.book import BookCreate

    repo = BookRepository(session)
    created_book = await repo.create_from_metadata(
        BookCreate(title="Book", authors=["Jane Doe", "jane doe", "JANE DOE"]),
        cover_path=None,
    )
    await session.flush()
    await session.refresh(created_book, attribute_names=["authors"])

    assert len(created_book.authors) == 1
    assert created_book.authors[0].name == "Jane Doe"


@pytest.mark.asyncio
async def test_repo_empty_author_strings_are_skipped(session: AsyncSession) -> None:
    """Empty/whitespace author names don't create empty Author rows."""
    from shelvr.db.models import Author
    from shelvr.repositories.books import BookRepository
    from shelvr.schemas.book import BookCreate

    repo = BookRepository(session)
    created_book = await repo.create_from_metadata(
        BookCreate(title="Book", authors=["Real Author", "", "   "]),
        cover_path=None,
    )
    await session.flush()
    await session.refresh(created_book, attribute_names=["authors"])

    assert len(created_book.authors) == 1
    assert created_book.authors[0].name == "Real Author"

    author_rows = await session.execute(select(Author))
    assert len(author_rows.scalars().all()) == 1

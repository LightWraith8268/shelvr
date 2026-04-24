"""Repository for book-centric database operations.

The sole DB-access surface for creating books, looking them up by hash, and
attaching formats. API routes and services must not touch SQLAlchemy sessions
directly -- they construct a BookRepository and call its methods.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.db.models import Author, Book, Format, Identifier, Tag
from shelvr.db.models.book import book_authors
from shelvr.schemas.book import BookCreate


class BookRepository:
    """All write and lookup operations for books go through here."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_books(
        self,
        *,
        limit: int,
        offset: int,
        sort: str,
        query: str | None,
    ) -> tuple[list[Book], int]:
        """Return a page of books plus total match count.

        sort: "title" (asc on sort_title coalesced with title) or "added" (desc on date_added).
        query: optional case-insensitive substring match on title or author name.
        """
        base_statement = select(Book)
        count_statement = select(func.count()).select_from(Book)

        if query:
            pattern = f"%{query.lower()}%"
            author_subquery = (
                select(book_authors.c.book_id)
                .join(Author, Author.id == book_authors.c.author_id)
                .where(func.lower(Author.name).like(pattern))
            )
            filter_condition = or_(
                func.lower(Book.title).like(pattern),
                Book.id.in_(author_subquery),
            )
            base_statement = base_statement.where(filter_condition)
            count_statement = count_statement.where(filter_condition)

        if sort == "title":
            base_statement = base_statement.order_by(func.coalesce(Book.sort_title, Book.title))
        else:
            base_statement = base_statement.order_by(Book.date_added.desc(), Book.id.desc())

        base_statement = base_statement.limit(limit).offset(offset)

        rows_result = await self._session.execute(base_statement)
        books = list(rows_result.scalars().all())

        count_result = await self._session.execute(count_statement)
        total = int(count_result.scalar_one())

        return books, total

    async def get_by_hash(self, file_hash: str) -> Book | None:
        """Return the Book that owns a Format with the given file_hash, or None."""
        lookup_statement = (
            select(Book)
            .join(Format, Format.book_id == Book.id)
            .where(Format.file_hash == file_hash)
        )
        query_result = await self._session.execute(lookup_statement)
        return query_result.scalars().first()

    async def create_from_metadata(self, metadata: BookCreate, cover_path: str | None) -> Book:
        """Create a Book with its Authors / Tags / Identifiers.

        The caller is responsible for flushing or committing the session.
        """
        new_book = Book(
            title=metadata.title,
            sort_title=metadata.sort_title or _compute_sort_title(metadata.title),
            series_index=metadata.series_index,
            description=metadata.description,
            language=metadata.language,
            publisher=metadata.publisher,
            published_date=_parse_published_date(metadata.published_date),
            isbn=metadata.isbn,
            cover_path=cover_path,
        )

        for author_name in _dedupe_preserving_order(metadata.authors):
            author_row = await self._get_or_create_author(author_name)
            new_book.authors.append(author_row)

        for tag_name in _dedupe_preserving_order(metadata.tags):
            tag_row = await self._get_or_create_tag(tag_name)
            new_book.tags.append(tag_row)

        self._session.add(new_book)
        await self._session.flush()  # populate new_book.id for identifier rows

        for scheme, value in metadata.identifiers.items():
            if not scheme or not value:
                continue
            self._session.add(Identifier(book_id=new_book.id, scheme=scheme, value=value))

        return new_book

    async def add_format(
        self,
        *,
        book_id: int,
        format: str,
        file_path: str,
        file_size: int,
        file_hash: str,
        source: str = "import",
    ) -> Format:
        """Attach a Format record to an existing book."""
        new_format = Format(
            book_id=book_id,
            format=format,
            file_path=file_path,
            file_size=file_size,
            file_hash=file_hash,
            source=source,
        )
        self._session.add(new_format)
        return new_format

    async def _get_or_create_author(self, name: str) -> Author:
        """Return an existing Author by name, or create one."""
        lookup_statement = select(Author).where(Author.name == name)
        query_result = await self._session.execute(lookup_statement)
        existing_author = query_result.scalars().first()
        if existing_author is not None:
            return existing_author
        new_author = Author(name=name, sort_name=_compute_sort_name(name))
        self._session.add(new_author)
        await self._session.flush()
        return new_author

    async def _get_or_create_tag(self, name: str) -> Tag:
        """Return an existing Tag by name, or create one."""
        lookup_statement = select(Tag).where(Tag.name == name)
        query_result = await self._session.execute(lookup_statement)
        existing_tag = query_result.scalars().first()
        if existing_tag is not None:
            return existing_tag
        new_tag = Tag(name=name)
        self._session.add(new_tag)
        await self._session.flush()
        return new_tag


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    """Trim, drop empties, and dedupe case-insensitively. First occurrence wins."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        trimmed = raw.strip()
        if not trimmed:
            continue
        key = trimmed.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(trimmed)
    return out


def _compute_sort_title(title: str) -> str | None:
    """Return 'Great Gatsby, The' for 'The Great Gatsby'. Else None."""
    for article in ("The ", "A ", "An "):
        if title.startswith(article):
            return f"{title[len(article) :]}, {article.strip()}"
    return None


def _compute_sort_name(name: str) -> str | None:
    """Return 'Le Guin, Ursula K.' for 'Ursula K. Le Guin'. Best-effort."""
    name_parts = name.split()
    if len(name_parts) < 2:
        return None
    last_name = name_parts[-1]
    rest_of_name = " ".join(name_parts[:-1])
    return f"{last_name}, {rest_of_name}"


def _parse_published_date(raw: str | None) -> date | None:
    """Parse YYYY-MM-DD (or a prefix thereof) into a date, else return None.

    The Book model's published_date column is a Date; format readers surface
    strings. Best-effort -- incomplete inputs (just 'YYYY' or 'YYYY-MM') yield
    None because a Date column requires full YYYY-MM-DD.
    """
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None

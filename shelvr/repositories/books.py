"""Repository for book-centric database operations.

The sole DB-access surface for creating books, looking them up by hash, and
attaching formats. API routes and services must not touch SQLAlchemy sessions
directly -- they construct a BookRepository and call its methods.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.db.models import Author, Book, Format, Identifier, Series, Tag
from shelvr.db.models.book import book_authors, book_tags
from shelvr.schemas.book import BookCreate, BookUpdate


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
        tag: str | None = None,
        author_id: int | None = None,
        language: str | None = None,
        series_id: int | None = None,
    ) -> tuple[list[Book], int]:
        """Return a page of books plus total match count.

        sort: "title" (asc on sort_title coalesced with title) or "added" (desc on date_added).
        query: optional case-insensitive substring match on title or author name.
        tag/author_id/language: optional exact-match filters (tag and language case-insensitive).
        """
        base_statement = select(Book)
        count_statement = select(func.count()).select_from(Book)

        filters = []

        if query:
            pattern = f"%{query.lower()}%"
            author_subquery = (
                select(book_authors.c.book_id)
                .join(Author, Author.id == book_authors.c.author_id)
                .where(func.lower(Author.name).like(pattern))
            )
            filters.append(or_(func.lower(Book.title).like(pattern), Book.id.in_(author_subquery)))

        if tag:
            tag_subquery = (
                select(book_tags.c.book_id)
                .join(Tag, Tag.id == book_tags.c.tag_id)
                .where(func.lower(Tag.name) == tag.lower())
            )
            filters.append(Book.id.in_(tag_subquery))

        if author_id is not None:
            author_subquery_id = select(book_authors.c.book_id).where(
                book_authors.c.author_id == author_id
            )
            filters.append(Book.id.in_(author_subquery_id))

        if language:
            filters.append(func.lower(Book.language) == language.lower())

        if series_id is not None:
            filters.append(Book.series_id == series_id)

        for filter_condition in filters:
            base_statement = base_statement.where(filter_condition)
            count_statement = count_statement.where(filter_condition)

        if sort == "title":
            base_statement = base_statement.order_by(func.coalesce(Book.sort_title, Book.title))
        elif sort == "series":
            # Group by series, then by index within. Books without a series fall to the end.
            base_statement = base_statement.order_by(
                Book.series_id.is_(None),
                func.coalesce(Book.series_id, 0),
                func.coalesce(Book.series_index, 0),
                func.coalesce(Book.sort_title, Book.title),
            )
        else:
            base_statement = base_statement.order_by(Book.date_added.desc(), Book.id.desc())

        base_statement = base_statement.limit(limit).offset(offset)

        rows_result = await self._session.execute(base_statement)
        books = list(rows_result.scalars().all())

        count_result = await self._session.execute(count_statement)
        total = int(count_result.scalar_one())

        return books, total

    async def list_tags_with_counts(self, *, limit: int = 200) -> list[tuple[Tag, int]]:
        """Return tags ordered by usage count desc, then alpha. Tags with zero books are excluded."""
        statement = (
            select(Tag, func.count(book_tags.c.book_id).label("count"))
            .join(book_tags, Tag.id == book_tags.c.tag_id)
            .group_by(Tag.id)
            .order_by(func.count(book_tags.c.book_id).desc(), Tag.name)
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return [(row[0], int(row[1])) for row in result.all()]

    async def list_authors_with_counts(self, *, limit: int = 200) -> list[tuple[Author, int]]:
        """Return authors ordered by usage count desc, then alpha. Authors with zero books are excluded."""
        statement = (
            select(Author, func.count(book_authors.c.book_id).label("count"))
            .join(book_authors, Author.id == book_authors.c.author_id)
            .group_by(Author.id)
            .order_by(
                func.count(book_authors.c.book_id).desc(),
                func.coalesce(Author.sort_name, Author.name),
            )
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return [(row[0], int(row[1])) for row in result.all()]

    async def list_languages_with_counts(self) -> list[tuple[str, int]]:
        """Return non-empty book languages with their counts, ordered by count desc."""
        statement = (
            select(Book.language, func.count(Book.id).label("count"))
            .where(Book.language.is_not(None))
            .group_by(Book.language)
            .order_by(func.count(Book.id).desc(), Book.language)
        )
        result = await self._session.execute(statement)
        return [(row[0], int(row[1])) for row in result.all() if row[0]]

    async def get_book(self, book_id: int) -> Book | None:
        """Return a Book by id, or None."""
        lookup_statement = select(Book).where(Book.id == book_id)
        query_result = await self._session.execute(lookup_statement)
        return query_result.scalars().first()

    async def get_format(self, format_id: int) -> Format | None:
        """Return a Format by id, or None."""
        lookup_statement = select(Format).where(Format.id == format_id)
        query_result = await self._session.execute(lookup_statement)
        return query_result.scalars().first()

    async def get_identifiers(self, book_id: int) -> dict[str, str]:
        """Return scheme→value map for a book's identifiers."""
        lookup_statement = select(Identifier).where(Identifier.book_id == book_id)
        query_result = await self._session.execute(lookup_statement)
        return {row.scheme: row.value for row in query_result.scalars().all()}

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
        series_row: Series | None = None
        if metadata.series:
            series_row = await self._get_or_create_series(metadata.series.strip())

        new_book = Book(
            title=metadata.title,
            sort_title=metadata.sort_title or _compute_sort_title(metadata.title),
            series_id=series_row.id if series_row is not None else None,
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

    async def update_book(self, book_id: int, update: BookUpdate) -> Book | None:
        """Apply a partial update to a book. Returns the updated Book, or None if missing.

        ``authors`` and ``tags`` lists, when provided, replace the existing
        association rows. Omitted fields are left untouched.
        """
        book = await self.get_book(book_id)
        if book is None:
            return None

        update_data = update.model_dump(exclude_unset=True)

        # Pop relationship/derived fields so they don't go through setattr.
        author_names = update_data.pop("authors", None)
        tag_names = update_data.pop("tags", None)
        series_field_provided = "series" in update_data
        series_value = update_data.pop("series", None)

        if "title" in update_data and "sort_title" not in update_data:
            update_data["sort_title"] = _compute_sort_title(update_data["title"])

        if series_field_provided:
            if series_value:
                series_row = await self._get_or_create_series(series_value.strip())
                book.series_id = series_row.id
            else:
                book.series_id = None

        for field, value in update_data.items():
            setattr(book, field, value)

        # Hydrate the relationship collections before mutating them so the
        # subsequent .clear() doesn't trigger an implicit lazy-load.
        if author_names is not None or tag_names is not None:
            await self._session.refresh(book, attribute_names=["authors", "tags"])

        if author_names is not None:
            book.authors.clear()
            for author_name in _dedupe_preserving_order(author_names):
                author_row = await self._get_or_create_author(author_name)
                book.authors.append(author_row)

        if tag_names is not None:
            book.tags.clear()
            for tag_name in _dedupe_preserving_order(tag_names):
                tag_row = await self._get_or_create_tag(tag_name)
                book.tags.append(tag_row)

        await self._session.flush()
        # Full refresh — onupdate column (date_modified) needs reload, plus
        # any attribute the response builder might read.
        await self._session.refresh(book)
        await self._session.refresh(book, attribute_names=["authors", "tags", "formats"])
        return book

    async def delete_book(self, book_id: int) -> Book | None:
        """Delete a book row, returning the deleted ORM instance for cleanup work.

        Cascades to formats and association tables via FK ``ON DELETE CASCADE``.
        File cleanup on disk is the caller's responsibility — the repo only
        owns the DB.
        """
        book = await self.get_book(book_id)
        if book is None:
            return None
        # Hydrate formats while still attached so the caller can use them.
        await self._session.refresh(book, attribute_names=["formats"])
        await self._session.delete(book)
        await self._session.flush()
        return book

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

    async def _get_or_create_series(self, name: str) -> Series:
        """Return an existing Series by name, or create one."""
        lookup_statement = select(Series).where(Series.name == name)
        query_result = await self._session.execute(lookup_statement)
        existing_series = query_result.scalars().first()
        if existing_series is not None:
            return existing_series
        new_series = Series(name=name, sort_name=_compute_sort_title(name) or name)
        self._session.add(new_series)
        await self._session.flush()
        return new_series

    async def list_series_with_counts(self, *, limit: int = 200) -> list[tuple[Series, int]]:
        """Return series ordered by usage count desc, then alpha. Empty series excluded."""
        statement = (
            select(Series, func.count(Book.id).label("count"))
            .join(Book, Book.series_id == Series.id)
            .group_by(Series.id)
            .order_by(func.count(Book.id).desc(), func.coalesce(Series.sort_name, Series.name))
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return [(row[0], int(row[1])) for row in result.all()]


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

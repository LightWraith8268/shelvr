"""SQLAlchemy model re-exports."""

from __future__ import annotations

from shelvr.db.models.author import Author
from shelvr.db.models.book import Book, book_authors, book_tags
from shelvr.db.models.format import Format
from shelvr.db.models.series import Series
from shelvr.db.models.tag import Tag

__all__ = ["Author", "Book", "Format", "Series", "Tag", "book_authors", "book_tags"]

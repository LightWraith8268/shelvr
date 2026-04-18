"""SQLAlchemy model re-exports."""

from __future__ import annotations

from shelvr.db.models.author import Author
from shelvr.db.models.book import Book, book_authors, book_tags
from shelvr.db.models.device import Device
from shelvr.db.models.format import Format
from shelvr.db.models.identifier import Identifier
from shelvr.db.models.reading_progress import ReadingProgress
from shelvr.db.models.series import Series
from shelvr.db.models.tag import Tag
from shelvr.db.models.user import User

__all__ = [
    "Author",
    "Book",
    "Device",
    "Format",
    "Identifier",
    "ReadingProgress",
    "Series",
    "Tag",
    "User",
    "book_authors",
    "book_tags",
]

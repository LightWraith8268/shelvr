"""Pydantic schemas for book-related requests and responses."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class AuthorRead(BaseModel):
    """Author output shape."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sort_name: str | None = None


class TagRead(BaseModel):
    """Tag output shape."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str | None = None


class FormatRead(BaseModel):
    """Format output shape — one concrete ebook file per book."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    format: str
    file_path: str
    file_size: int
    file_hash: str
    source: str
    date_added: datetime


class BookCreate(BaseModel):
    """Shape used internally when the importer service creates a book.

    Not an HTTP request body — the upload endpoint accepts multipart form data
    and builds this from the format reader's Metadata output.
    """

    title: str = Field(..., min_length=1)
    sort_title: str | None = None
    authors: list[str] = Field(default_factory=list)
    series: str | None = None
    series_index: float | None = None
    description: str | None = None
    language: str | None = None
    publisher: str | None = None
    published_date: str | None = None  # String because format readers surface partial dates
    isbn: str | None = None
    tags: list[str] = Field(default_factory=list)
    identifiers: dict[str, str] = Field(default_factory=dict)


class BookUpdate(BaseModel):
    """Partial update — all fields optional.

    ``authors`` and ``tags``, when provided, replace the entire list. Pass an
    empty list to clear them; omit the field to leave it untouched.
    """

    title: str | None = Field(default=None, min_length=1, max_length=1000)
    sort_title: str | None = None
    series: str | None = None
    series_index: float | None = None
    description: str | None = None
    language: str | None = None
    publisher: str | None = None
    published_date: date | None = None
    isbn: str | None = None
    rating: int | None = Field(default=None, ge=0, le=10)
    authors: list[str] | None = None
    tags: list[str] | None = None


class BookRead(BaseModel):
    """Book output shape returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    sort_title: str | None
    authors: list[AuthorRead]
    series: str | None
    series_id: int | None = None
    series_index: float | None
    description: str | None
    language: str | None
    publisher: str | None
    published_date: date | None = None
    isbn: str | None
    rating: int | None
    tags: list[TagRead] = Field(default_factory=list)
    identifiers: dict[str, str] = Field(default_factory=dict)
    formats: list[FormatRead]
    date_added: datetime
    date_modified: datetime
    cover_path: str | None


class BookList(BaseModel):
    """Paginated book list response."""

    items: list[BookRead]
    total: int
    limit: int
    offset: int


class BulkDeleteRequest(BaseModel):
    """Body for POST /api/v1/books/bulk-delete."""

    ids: list[int] = Field(..., min_length=1, max_length=500)


class BulkDeleteResponse(BaseModel):
    """Result of a bulk delete: which ids actually went through."""

    deleted: list[int]
    not_found: list[int]

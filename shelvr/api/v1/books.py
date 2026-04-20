"""POST /api/v1/books — multipart file upload to import a book."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.api.deps import get_plugin_registry, get_session, get_settings
from shelvr.config import Settings
from shelvr.db.models import Book
from shelvr.formats.base import FormatReadError, UnsupportedFormatError
from shelvr.plugins import PluginRegistry
from shelvr.repositories.books import BookRepository
from shelvr.schemas.book import BookRead
from shelvr.services.hashing import sha256_bytes
from shelvr.services.importer import import_file

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=BookRead)
async def upload_book(
    response: Response,
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    plugin_registry: PluginRegistry = Depends(get_plugin_registry),
) -> dict[str, Any]:
    """Import a book file. Returns 201 on new book, 200 on dedup hit."""
    file_bytes = await file.read()
    filename = file.filename or "upload"

    repo = BookRepository(session)
    upload_hash = sha256_bytes(file_bytes)
    existing_book = await repo.get_by_hash(upload_hash)
    is_new_upload = existing_book is None

    try:
        imported_book = await import_file(
            file_bytes=file_bytes,
            original_filename=filename,
            library_root=settings.library_path,
            session=session,
            plugin_registry=plugin_registry,
        )
    except UnsupportedFormatError as unsupported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(unsupported)
        ) from unsupported
    except FormatReadError as read_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(read_error)
        ) from read_error

    await session.commit()
    await session.refresh(imported_book, attribute_names=["authors", "tags", "formats"])

    response.status_code = status.HTTP_201_CREATED if is_new_upload else status.HTTP_200_OK
    return _book_to_response_dict(imported_book)


def _book_to_response_dict(book: Book) -> dict[str, Any]:
    """Build a BookRead-compatible dict from a Book ORM instance.

    v1 deliberately does not surface the Identifier rows as a map — identifiers
    are stored but the response body keeps them empty. We'll wire up the proper
    response mapping when we add the GET /books/{id} endpoint.
    """
    return {
        "id": book.id,
        "title": book.title,
        "sort_title": book.sort_title,
        "authors": [{"id": a.id, "name": a.name, "sort_name": a.sort_name} for a in book.authors],
        "series": None,
        "series_index": book.series_index,
        "description": book.description,
        "language": book.language,
        "publisher": book.publisher,
        "published_date": book.published_date,
        "isbn": book.isbn,
        "rating": book.rating,
        "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in book.tags],
        "identifiers": {},
        "formats": [
            {
                "id": f.id,
                "format": f.format,
                "file_path": f.file_path,
                "file_size": f.file_size,
                "file_hash": f.file_hash,
                "source": f.source,
                "date_added": f.date_added,
            }
            for f in book.formats
        ],
        "date_added": book.date_added,
        "date_modified": book.date_modified,
        "cover_path": book.cover_path,
    }

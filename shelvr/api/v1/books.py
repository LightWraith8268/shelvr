"""Book endpoints: list, detail, upload, cover."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.api.deps import get_plugin_registry, get_session, get_settings
from shelvr.auth.deps import get_current_user, require_admin
from shelvr.config import Settings
from shelvr.db.models import Book, User
from shelvr.formats.base import FormatReadError, UnsupportedFormatError
from shelvr.plugins import PluginRegistry
from shelvr.repositories.books import BookRepository
from shelvr.schemas.book import BookList, BookRead, BookUpdate
from shelvr.services.hashing import sha256_bytes
from shelvr.services.importer import import_file

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=BookList)
async def list_books(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort: Literal["title", "added", "series"] = Query(default="added"),
    q: str | None = Query(default=None, min_length=1, max_length=200),
    tag: str | None = Query(default=None, min_length=1, max_length=200),
    author_id: int | None = Query(default=None, ge=1),
    language: str | None = Query(default=None, min_length=1, max_length=20),
    series_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List books with pagination, sort, search, and tag/author/language/series filters."""
    repo = BookRepository(session)
    books, total = await repo.list_books(
        limit=limit,
        offset=offset,
        sort=sort,
        query=q,
        tag=tag,
        author_id=author_id,
        language=language,
        series_id=series_id,
    )
    return {
        "items": [_book_to_response_dict(b) for b in books],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{book_id}", response_model=BookRead)
async def get_book(
    book_id: int,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return a single book by id, including identifiers."""
    repo = BookRepository(session)
    book = await repo.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")
    identifiers = await repo.get_identifiers(book_id)
    return _book_to_response_dict(book, identifiers=identifiers)


@router.get("/{book_id}/cover")
async def get_book_cover(
    book_id: int,
    size: Literal["original", "small", "medium"] = Query(default="medium"),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Stream the book's cover JPEG. Defaults to medium thumbnail."""
    repo = BookRepository(session)
    book = await repo.get_book(book_id)
    if book is None or not book.cover_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cover not found")

    cover_relative = Path(book.cover_path)
    if size != "original":
        cover_relative = cover_relative.with_name(f"cover-{size}.jpg")

    cover_absolute = (settings.library_path / cover_relative).resolve()
    library_root = settings.library_path.resolve()
    if not _is_within(cover_absolute, library_root) or not cover_absolute.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cover not found")

    return FileResponse(cover_absolute, media_type="image/jpeg")


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


@router.patch("/{book_id}", response_model=BookRead)
async def update_book(
    book_id: int,
    update: BookUpdate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """Apply a partial metadata update to a book. Admin only."""
    repo = BookRepository(session)
    updated = await repo.update_book(book_id, update)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")
    await session.commit()
    await session.refresh(updated, attribute_names=["authors", "tags", "formats"])
    identifiers = await repo.get_identifiers(book_id)
    return _book_to_response_dict(updated, identifiers=identifiers)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _admin: User = Depends(require_admin),
) -> Response:
    """Delete a book and remove its files from the library directory. Admin only."""
    repo = BookRepository(session)
    book = await repo.delete_book(book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")

    library_root = settings.library_path.resolve()
    paths_to_remove: list[Path] = []
    for book_format in book.formats:
        candidate = (settings.library_path / book_format.file_path).resolve()
        if _is_within(candidate, library_root) and candidate.is_file():
            paths_to_remove.append(candidate)
    if book.cover_path:
        cover_candidate = (settings.library_path / book.cover_path).resolve()
        if _is_within(cover_candidate, library_root) and cover_candidate.is_file():
            paths_to_remove.append(cover_candidate)
            cover_dir = cover_candidate.parent
            for size in ("small", "medium"):
                sized = cover_dir / f"cover-{size}.jpg"
                if sized.is_file():
                    paths_to_remove.append(sized)

    await session.commit()

    for file_path in paths_to_remove:
        try:
            file_path.unlink()
        except OSError:
            # Best-effort cleanup — DB row is already gone, file removal is
            # a janitor task, not a correctness invariant.
            continue

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=BookRead)
async def upload_book(
    response: Response,
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    plugin_registry: PluginRegistry = Depends(get_plugin_registry),
    _admin: User = Depends(require_admin),
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


def _book_to_response_dict(
    book: Book, *, identifiers: dict[str, str] | None = None
) -> dict[str, Any]:
    """Build a BookRead-compatible dict from a Book ORM instance."""
    return {
        "id": book.id,
        "title": book.title,
        "sort_title": book.sort_title,
        "authors": [{"id": a.id, "name": a.name, "sort_name": a.sort_name} for a in book.authors],
        "series": book.series.name if book.series is not None else None,
        "series_index": book.series_index,
        "description": book.description,
        "language": book.language,
        "publisher": book.publisher,
        "published_date": book.published_date,
        "isbn": book.isbn,
        "rating": book.rating,
        "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in book.tags],
        "identifiers": identifiers or {},
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

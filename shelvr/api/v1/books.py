"""Book endpoints: list, detail, upload, cover."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from PIL import UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.api.deps import get_plugin_registry, get_session, get_settings
from shelvr.auth.deps import get_current_user, require_admin
from shelvr.config import Settings
from shelvr.db.models import Book, User
from shelvr.formats.base import FormatReadError, UnsupportedFormatError
from shelvr.plugins import PluginRegistry
from shelvr.repositories.bookmarks import BookmarkRepository
from shelvr.repositories.books import BookRepository
from shelvr.repositories.highlights import HighlightRepository
from shelvr.repositories.reading_progress import ReadingProgressRepository
from shelvr.schemas.book import (
    BookList,
    BookRead,
    BookUpdate,
    BulkDeleteRequest,
    BulkDeleteResponse,
    BulkTagRequest,
    BulkTagResponse,
)
from shelvr.schemas.bookmark import BookmarkCreate, BookmarkRead
from shelvr.schemas.highlight import HighlightCreate, HighlightRead, HighlightUpdate
from shelvr.schemas.reading_progress import ReadingProgressRead, ReadingProgressUpsert
from shelvr.schemas.sync import Locator, LocatorLocations
from shelvr.services.covers import save_cover
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


_ACCEPTED_COVER_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/avif",
}


@router.put("/{book_id}/cover", response_model=BookRead)
async def replace_book_cover(
    book_id: int,
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """Replace a book's cover image and regenerate the sized thumbnails. Admin only."""
    if file.content_type and file.content_type not in _ACCEPTED_COVER_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported cover type: {file.content_type}",
        )

    repo = BookRepository(session)
    book = await repo.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")

    await session.refresh(book, attribute_names=["formats"])

    library_root = settings.library_path.resolve()
    if book.cover_path:
        dest_dir = (settings.library_path / book.cover_path).resolve().parent
    elif book.formats:
        dest_dir = (settings.library_path / book.formats[0].file_path).resolve().parent
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="book has no formats — cannot derive a destination directory",
        )

    if not _is_within(dest_dir, library_root):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="resolved cover directory escaped the library root",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cover file is empty")

    try:
        saved = save_cover(image_bytes, dest_dir)
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="not a valid image"
        ) from exc

    cover_relative = str(saved["original"].relative_to(library_root)).replace("\\", "/")
    book.cover_path = cover_relative
    await session.commit()
    await session.refresh(book)
    await session.refresh(book, attribute_names=["authors", "tags", "formats"])
    identifiers = await repo.get_identifiers(book_id)
    return _book_to_response_dict(book, identifiers=identifiers)


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


@router.get("/{book_id}/progress", response_model=ReadingProgressRead | None)
async def get_progress(
    book_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ReadingProgressRead | None:
    """Return the current user's reading position for the book, or null if none."""
    book_repo = BookRepository(session)
    if await book_repo.get_book(book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")
    progress = await ReadingProgressRepository(session).get(book_id=book_id, user_id=user.id)
    if progress is None:
        return None
    return ReadingProgressRead.model_validate(progress)


@router.put("/{book_id}/progress", response_model=ReadingProgressRead)
async def put_progress(
    book_id: int,
    body: ReadingProgressUpsert,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ReadingProgressRead:
    """Upsert the current user's reading position for the book."""
    book_repo = BookRepository(session)
    if await book_repo.get_book(book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")
    progress = await ReadingProgressRepository(session).upsert(
        book_id=book_id, user_id=user.id, locator=body.locator, percent=body.percent
    )
    await session.commit()
    return ReadingProgressRead.model_validate(progress)


@router.delete("/{book_id}/progress", status_code=status.HTTP_204_NO_CONTENT)
async def delete_progress(
    book_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    """Clear the current user's reading position. Idempotent."""
    book_repo = BookRepository(session)
    if await book_repo.get_book(book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")
    await ReadingProgressRepository(session).delete(book_id=book_id, user_id=user.id)
    await session.commit()
    return None


@router.get("/{book_id}/sync", response_model=Locator | None)
async def get_sync_locator(
    book_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Locator | None:
    """Return the current user's position as a Readium Locator, or null if unset."""
    book_repo = BookRepository(session)
    if await book_repo.get_book(book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")
    progress = await ReadingProgressRepository(session).get(book_id=book_id, user_id=user.id)
    if progress is None:
        return None
    return Locator(
        locations=LocatorLocations(totalProgression=progress.percent, fragment=[progress.locator]),
        modified=progress.updated_at,
    )


@router.put("/{book_id}/sync", response_model=Locator)
async def put_sync_locator(
    book_id: int,
    body: Locator,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Locator:
    """Upsert the current user's position from a Readium Locator.

    Reads ``locations.fragment[0]`` as the opaque locator and
    ``locations.totalProgression`` (falling back to ``progression``) as the
    percent. Locators with neither a fragment nor a progression are rejected.
    """
    book_repo = BookRepository(session)
    if await book_repo.get_book(book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")
    locator_value = body.locations.fragment[0] if body.locations.fragment else None
    if not locator_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="locations.fragment must contain at least one locator",
        )
    percent = body.locations.total_progression
    if percent is None:
        percent = body.locations.progression
    if percent is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="locations.totalProgression or locations.progression is required",
        )
    progress = await ReadingProgressRepository(session).upsert(
        book_id=book_id, user_id=user.id, locator=locator_value, percent=percent
    )
    await session.commit()
    return Locator(
        locations=LocatorLocations(totalProgression=progress.percent, fragment=[progress.locator]),
        modified=progress.updated_at,
    )


@router.get("/{book_id}/bookmarks", response_model=list[BookmarkRead])
async def list_bookmarks(
    book_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[BookmarkRead]:
    """List the current user's bookmarks for the book, oldest first."""
    book_repo = BookRepository(session)
    if await book_repo.get_book(book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")
    rows = await BookmarkRepository(session).list_for_book(book_id=book_id, user_id=user.id)
    return [BookmarkRead.model_validate(row) for row in rows]


@router.post(
    "/{book_id}/bookmarks", response_model=BookmarkRead, status_code=status.HTTP_201_CREATED
)
async def create_bookmark(
    book_id: int,
    body: BookmarkCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> BookmarkRead:
    """Create a bookmark for the current user on the given book."""
    book_repo = BookRepository(session)
    if await book_repo.get_book(book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")
    bookmark = await BookmarkRepository(session).create(
        book_id=book_id, user_id=user.id, locator=body.locator, label=body.label
    )
    await session.commit()
    return BookmarkRead.model_validate(bookmark)


@router.delete("/{book_id}/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    book_id: int,
    bookmark_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    """Delete one of the current user's bookmarks. 404 if it doesn't belong to them."""
    repo = BookmarkRepository(session)
    existing = await repo.get(bookmark_id=bookmark_id, user_id=user.id)
    if existing is None or existing.book_id != book_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="bookmark not found")
    await repo.delete(bookmark_id=bookmark_id, user_id=user.id)
    await session.commit()
    return None


@router.get("/{book_id}/highlights", response_model=list[HighlightRead])
async def list_highlights(
    book_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[HighlightRead]:
    """List the current user's highlights for the book, oldest first."""
    book_repo = BookRepository(session)
    if await book_repo.get_book(book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")
    rows = await HighlightRepository(session).list_for_book(book_id=book_id, user_id=user.id)
    return [HighlightRead.model_validate(row) for row in rows]


@router.post(
    "/{book_id}/highlights",
    response_model=HighlightRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_highlight(
    book_id: int,
    body: HighlightCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> HighlightRead:
    """Create a highlight for the current user on the given book."""
    book_repo = BookRepository(session)
    if await book_repo.get_book(book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")
    highlight = await HighlightRepository(session).create(
        book_id=book_id,
        user_id=user.id,
        locator_range=body.locator_range,
        text=body.text,
        color=body.color,
        note=body.note,
    )
    await session.commit()
    return HighlightRead.model_validate(highlight)


@router.patch("/{book_id}/highlights/{highlight_id}", response_model=HighlightRead)
async def update_highlight(
    book_id: int,
    highlight_id: int,
    body: HighlightUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> HighlightRead:
    """Update color and/or note. Pass clear_note=true to remove an existing note."""
    repo = HighlightRepository(session)
    existing = await repo.get(highlight_id=highlight_id, user_id=user.id)
    if existing is None or existing.book_id != book_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="highlight not found")
    updated = await repo.update(
        highlight_id=highlight_id,
        user_id=user.id,
        color=body.color,
        note=body.note,
        clear_note=body.clear_note,
    )
    assert updated is not None  # existence checked above
    await session.commit()
    return HighlightRead.model_validate(updated)


@router.delete("/{book_id}/highlights/{highlight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_highlight(
    book_id: int,
    highlight_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    """Delete one of the current user's highlights. 404 if it doesn't belong to them."""
    repo = HighlightRepository(session)
    existing = await repo.get(highlight_id=highlight_id, user_id=user.id)
    if existing is None or existing.book_id != book_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="highlight not found")
    await repo.delete(highlight_id=highlight_id, user_id=user.id)
    await session.commit()
    return None


@router.post("/bulk-tag", response_model=BulkTagResponse)
async def bulk_tag_books(
    body: BulkTagRequest,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> BulkTagResponse:
    """Add and/or remove tags across a batch of books. Admin only."""
    if not body.add and not body.remove:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="at least one of add/remove must be non-empty",
        )
    repo = BookRepository(session)
    updated, not_found = await repo.bulk_tag(book_ids=body.ids, add=body.add, remove=body.remove)
    await session.commit()
    return BulkTagResponse(updated=updated, not_found=not_found)


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_books(
    body: BulkDeleteRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _admin: User = Depends(require_admin),
) -> BulkDeleteResponse:
    """Delete a batch of books in one call. Best-effort file cleanup per book.

    Admin only. Returns which ids were deleted and which didn't exist. Order
    of input ids is not preserved in the response.
    """
    repo = BookRepository(session)
    library_root = settings.library_path.resolve()
    deleted: list[int] = []
    not_found: list[int] = []
    paths_to_remove: list[Path] = []

    # Dedupe to avoid double-deleting and double-counting.
    for book_id in dict.fromkeys(body.ids):
        book = await repo.delete_book(book_id)
        if book is None:
            not_found.append(book_id)
            continue
        deleted.append(book_id)
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
            continue

    return BulkDeleteResponse(deleted=deleted, not_found=not_found)


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
        "series_id": book.series_id,
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

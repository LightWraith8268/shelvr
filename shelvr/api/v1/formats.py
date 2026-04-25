"""Format file streaming endpoint."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.api.deps import get_session, get_settings
from shelvr.auth.deps import get_current_user
from shelvr.config import Settings
from shelvr.db.models import User
from shelvr.repositories.books import BookRepository

router = APIRouter(prefix="/formats", tags=["formats"])

_MIME_BY_EXTENSION = {
    "epub": "application/epub+zip",
    "pdf": "application/pdf",
    "mobi": "application/x-mobipocket-ebook",
    "azw3": "application/vnd.amazon.ebook",
}


@router.get("/{format_id}/file")
async def download_format_file(
    format_id: int,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Stream the underlying ebook file for a format."""
    repo = BookRepository(session)
    format_row = await repo.get_format(format_id)
    if format_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="format not found")

    file_absolute = (settings.library_path / format_row.file_path).resolve()
    library_root = settings.library_path.resolve()
    try:
        file_absolute.relative_to(library_root)
    except ValueError as outside:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="format not found"
        ) from outside
    if not file_absolute.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="format not found")

    media_type = _MIME_BY_EXTENSION.get(
        format_row.format.lower(), mimetypes.guess_type(str(file_absolute))[0]
    )
    return FileResponse(
        file_absolute,
        media_type=media_type or "application/octet-stream",
        filename=Path(format_row.file_path).name,
    )

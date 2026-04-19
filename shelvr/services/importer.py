"""Top-level import orchestrator: bytes -> library directory -> database row."""

from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.db.models import Book
from shelvr.formats import get_reader_for_path
from shelvr.repositories.books import BookRepository
from shelvr.schemas.book import BookCreate
from shelvr.services.covers import save_cover
from shelvr.services.file_layout import compute_target_path
from shelvr.services.hashing import sha256_bytes


async def import_file(
    *,
    file_bytes: bytes,
    original_filename: str,
    library_root: Path,
    session: AsyncSession,
) -> Book:
    """Import a single ebook file.

    Steps:
        1. Hash the bytes.
        2. If a format already exists with this hash, return its book (dedup).
        3. Dispatch by extension to the right format reader.
        4. Write the bytes to a temp file so the reader can parse from disk.
        5. Read metadata + cover bytes.
        6. Compute target path under ``library_root`` and move the file there.
        7. Save cover + thumbnails alongside it.
        8. Create Book + Format + Authors + Tags + Identifiers via repository.

    Note: Metadata.extensions is captured by the format reader but not
    persisted in v1 -- will be wired up when v2's custom-columns feature lands.

    Returns:
        The created (or pre-existing) Book.

    Raises:
        UnsupportedFormatError: If no reader handles the file's extension.
        CorruptedFileError:     If the reader cannot parse the file.
    """
    repo = BookRepository(session)

    file_hash = sha256_bytes(file_bytes)
    existing_book = await repo.get_by_hash(file_hash)
    if existing_book is not None:
        return existing_book

    file_extension = Path(original_filename).suffix.lower()
    reader_module = get_reader_for_path(Path(original_filename))  # raises on unknown ext

    scratch_path = _write_scratch(file_bytes, file_extension)
    try:
        metadata = reader_module.read_metadata(scratch_path)
        cover_bytes = reader_module.extract_cover(scratch_path)
    finally:
        scratch_path.unlink(missing_ok=True)

    primary_author = metadata.authors[0] if metadata.authors else None
    target_path = compute_target_path(
        library_root=library_root,
        primary_author=primary_author,
        title=metadata.title,
        extension=file_extension,
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(file_bytes)

    cover_path_relative: str | None = None
    if cover_bytes:
        saved_covers = save_cover(cover_bytes, target_path.parent)
        cover_path_relative = str(saved_covers["original"].relative_to(library_root)).replace(
            "\\", "/"
        )

    file_path_relative = str(target_path.relative_to(library_root)).replace("\\", "/")
    book_create_data = BookCreate(
        title=metadata.title,
        authors=metadata.authors,
        series=metadata.series,
        series_index=metadata.series_index,
        description=metadata.description,
        language=metadata.language,
        publisher=metadata.publisher,
        published_date=metadata.published_date,
        isbn=metadata.isbn,
        tags=metadata.tags,
        identifiers=metadata.identifiers,
    )
    new_book = await repo.create_from_metadata(book_create_data, cover_path=cover_path_relative)
    await repo.add_format(
        book_id=new_book.id,
        format=file_extension.lstrip("."),
        file_path=file_path_relative,
        file_size=len(file_bytes),
        file_hash=file_hash,
        source="import",
    )
    return new_book


def _write_scratch(file_bytes: bytes, file_extension: str) -> Path:
    """Write bytes to a temp file with the right suffix and return its path."""
    with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as scratch_file:
        scratch_file.write(file_bytes)
        return Path(scratch_file.name)

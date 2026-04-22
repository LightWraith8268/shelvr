"""Top-level import orchestrator: bytes → library directory → database row."""

from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.db.models import Book
from shelvr.formats.base import (
    FormatImportResult,
    Metadata,
    UnsupportedFormatError,
)
from shelvr.plugins.registry import PluginRegistry
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
    plugin_registry: PluginRegistry,
) -> Book:
    """Import a single ebook file.

    Steps:
        1. Hash the bytes.
        2. If a format already exists with this hash, return its book (dedup).
        3. Dispatch the file to the ``on_format_import`` plugin hook;
           the first plugin to claim the extension returns a FormatImportResult.
        4. Write the bytes to the canonical library path.
        5. Save cover thumbnails.
        6. Create Book + Format + Authors + Tags + Identifiers via repository.
        7. Fire the ``on_book_added`` event hook.

    Note: Metadata.extensions is captured by the format plugin but not yet
    persisted — wires up when v2's custom-columns feature lands.

    Raises:
        UnsupportedFormatError: If no plugin claims the file's extension.
    """
    repo = BookRepository(session)

    file_hash = sha256_bytes(file_bytes)
    existing_book = await repo.get_by_hash(file_hash)
    if existing_book is not None:
        return existing_book

    file_extension = Path(original_filename).suffix.lower()

    scratch_path = _write_scratch(file_bytes, file_extension)
    try:
        import_result = await _run_format_plugins(
            plugin_registry, scratch_path, file_extension, original_filename
        )
    finally:
        scratch_path.unlink(missing_ok=True)

    metadata = import_result.metadata
    cover_bytes = import_result.cover_bytes

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
    book_create_data = _metadata_to_book_create(metadata)
    new_book = await repo.create_from_metadata(book_create_data, cover_path=cover_path_relative)
    await repo.add_format(
        book_id=new_book.id,
        format=file_extension.lstrip("."),
        file_path=file_path_relative,
        file_size=len(file_bytes),
        file_hash=file_hash,
        source="import",
    )

    await plugin_registry.fire_event("on_book_added", book=new_book)
    return new_book


async def _run_format_plugins(
    registry: PluginRegistry,
    scratch_path: Path,
    extension: str,
    original_filename: str,
) -> FormatImportResult:
    """Dispatch via the on_format_import handler hook; raise if no plugin claims it."""
    result = await registry.fire_handler("on_format_import", path=scratch_path, extension=extension)
    if result is None:
        raise UnsupportedFormatError(
            f"No format plugin handled {original_filename!r} (extension {extension!r})"
        )
    if not isinstance(result, FormatImportResult):
        raise TypeError(
            f"on_format_import returned {type(result).__name__}, expected FormatImportResult"
        )
    return result


def _metadata_to_book_create(metadata: Metadata) -> BookCreate:
    return BookCreate(
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


def _write_scratch(file_bytes: bytes, file_extension: str) -> Path:
    """Write bytes to a temp file with the right suffix and return its path."""
    with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as scratch_file:
        scratch_file.write(file_bytes)
        return Path(scratch_file.name)

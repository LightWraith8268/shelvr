"""Integration tests for the import pipeline orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "books"
BUILTIN_DIR = Path(__file__).parent.parent.parent / "shelvr" / "plugins" / "builtin"


def _load_builtin_registry():
    """Load all built-in format plugins into a fresh PluginRegistry."""
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    for loaded in PluginLoader(BUILTIN_DIR).discover():
        registry.register(loaded)
    return registry


@pytest.mark.asyncio
async def test_importer_creates_book_from_epub(session: AsyncSession, library_path: Path) -> None:
    """Importing an EPUB creates Book + Format + Author records + cover files."""
    from shelvr.services.importer import import_file

    epub_fixture = FIXTURE_DIR / "modest-proposal.epub"
    epub_bytes = epub_fixture.read_bytes()

    registry = _load_builtin_registry()

    imported_book = await import_file(
        file_bytes=epub_bytes,
        original_filename="modest-proposal.epub",
        library_root=library_path,
        session=session,
        plugin_registry=registry,
    )
    await session.flush()
    await session.refresh(imported_book, attribute_names=["authors", "tags", "formats"])

    assert imported_book.id is not None
    assert imported_book.title
    assert any("swift" in author.name.lower() for author in imported_book.authors)
    assert len(imported_book.formats) == 1
    assert imported_book.formats[0].file_hash

    author_dir = library_path / "Jonathan Swift"
    assert author_dir.exists()
    book_dirs = [subdir for subdir in author_dir.iterdir() if subdir.is_dir()]
    assert len(book_dirs) == 1
    book_dir = book_dirs[0]

    epub_files = list(book_dir.glob("*.epub"))
    assert len(epub_files) == 1

    assert (book_dir / "cover.jpg").exists()
    assert (book_dir / "cover-small.jpg").exists()
    assert (book_dir / "cover-medium.jpg").exists()


@pytest.mark.asyncio
async def test_importer_dedup_by_hash(session: AsyncSession, library_path: Path) -> None:
    """Uploading the same bytes twice returns the same book (idempotent)."""
    from shelvr.services.importer import import_file

    epub_fixture = FIXTURE_DIR / "modest-proposal.epub"
    epub_bytes = epub_fixture.read_bytes()

    registry = _load_builtin_registry()

    first_book = await import_file(
        file_bytes=epub_bytes,
        original_filename="modest-proposal.epub",
        library_root=library_path,
        session=session,
        plugin_registry=registry,
    )
    await session.flush()

    second_book = await import_file(
        file_bytes=epub_bytes,
        original_filename="renamed-but-same-bytes.epub",
        library_root=library_path,
        session=session,
        plugin_registry=registry,
    )
    await session.flush()

    assert first_book.id == second_book.id

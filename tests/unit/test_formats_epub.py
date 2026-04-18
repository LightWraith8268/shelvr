"""Tests for the EPUB format reader."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "books"


def test_epub_read_metadata_returns_title_and_author() -> None:
    """EPUB reader extracts title and author from the fixture."""
    from shelvr.formats.epub import read_metadata

    epub_files = list(FIXTURE_DIR.glob("*.epub"))
    assert epub_files, "No EPUB fixture found"
    fixture = epub_files[0]

    metadata = read_metadata(fixture)
    assert metadata.title
    # PG's Modest Proposal fixture has "Jonathan Swift" in DC:creator
    assert any("swift" in author.lower() for author in metadata.authors), (
        f"Expected a Swift author, got {metadata.authors}"
    )


def test_epub_read_metadata_raises_on_nonexistent_file() -> None:
    """Reading a path that doesn't exist raises FormatReadError."""
    from shelvr.formats.base import FormatReadError
    from shelvr.formats.epub import read_metadata

    with pytest.raises(FormatReadError):
        read_metadata(Path("/nonexistent/missing.epub"))


def test_epub_read_metadata_raises_on_wrong_format(tmp_path: Path) -> None:
    """Reading a non-EPUB file raises FormatReadError."""
    from shelvr.formats.base import FormatReadError
    from shelvr.formats.epub import read_metadata

    not_an_epub = tmp_path / "not-an-epub.epub"
    not_an_epub.write_bytes(b"plain text, not a zip, certainly not EPUB")

    with pytest.raises(FormatReadError):
        read_metadata(not_an_epub)


def test_epub_extract_cover_returns_bytes_or_none() -> None:
    """extract_cover returns bytes if the file has a cover, else None."""
    from shelvr.formats.epub import extract_cover

    epub_files = list(FIXTURE_DIR.glob("*.epub"))
    fixture = epub_files[0]

    result = extract_cover(fixture)
    assert result is None or isinstance(result, bytes)


def test_epub_extract_cover_pg_fixture_has_cover() -> None:
    """The real PG fixture we shipped has an embedded cover image."""
    from shelvr.formats.epub import extract_cover

    fixture = FIXTURE_DIR / "modest-proposal.epub"
    result = extract_cover(fixture)
    # PG's epub3.images variant has a cover. If it doesn't (e.g. if a later
    # implementer swapped the fixture for noimages), update this test to xfail
    # with a reason — don't delete it.
    assert result is not None, "Expected the PG fixture to have a cover image"
    assert len(result) > 0


def test_epub_extensions_tuple_handles_epub() -> None:
    """The module declares its handled file extensions."""
    from shelvr.formats.epub import EXTENSIONS

    assert ".epub" in EXTENSIONS
    # EXTENSIONS is a tuple, not a list — immutable registry contract
    assert isinstance(EXTENSIONS, tuple)

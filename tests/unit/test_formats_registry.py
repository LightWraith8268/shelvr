"""Tests for the format-reader registry."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "books"


def test_get_reader_for_epub() -> None:
    """Registry returns the EPUB reader module for .epub files."""
    from shelvr.formats import epub, get_reader_for_path

    reader = get_reader_for_path(Path("some.epub"))
    assert reader is epub


def test_get_reader_for_pdf() -> None:
    from shelvr.formats import get_reader_for_path, pdf

    reader = get_reader_for_path(Path("some.pdf"))
    assert reader is pdf


def test_get_reader_for_mobi() -> None:
    from shelvr.formats import get_reader_for_path, mobi

    reader = get_reader_for_path(Path("some.mobi"))
    assert reader is mobi


def test_get_reader_for_azw3_uses_mobi_reader() -> None:
    from shelvr.formats import get_reader_for_path, mobi

    reader = get_reader_for_path(Path("some.azw3"))
    assert reader is mobi


def test_get_reader_raises_on_unsupported_format() -> None:
    from shelvr.formats import get_reader_for_path
    from shelvr.formats.base import UnsupportedFormatError

    with pytest.raises(UnsupportedFormatError):
        get_reader_for_path(Path("some.xyz"))


def test_registry_dispatch_case_insensitive() -> None:
    """Extension matching is case-insensitive."""
    from shelvr.formats import epub, get_reader_for_path

    reader = get_reader_for_path(Path("SOME.EPUB"))
    assert reader is epub


def test_read_metadata_via_registry_end_to_end() -> None:
    """Registry-dispatched read_metadata works on a real fixture."""
    from shelvr.formats import get_reader_for_path

    epub_files = list(FIXTURE_DIR.glob("*.epub"))
    assert epub_files
    fixture = epub_files[0]

    reader = get_reader_for_path(fixture)
    metadata = reader.read_metadata(fixture)
    assert metadata.title


def test_registry_re_exports_public_types() -> None:
    """Registry re-exports Metadata and error types for convenience."""
    from shelvr.formats import (
        CorruptedFileError,
        FormatReadError,
        Metadata,
        UnsupportedFormatError,
    )

    assert Metadata is not None
    assert issubclass(CorruptedFileError, FormatReadError)
    assert issubclass(UnsupportedFormatError, FormatReadError)

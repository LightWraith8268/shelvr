"""Tests for the PDF format reader."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "books"


def test_pdf_read_metadata_returns_title_and_author() -> None:
    """PDF reader extracts title and author from the fixture."""
    from shelvr.formats.pdf import read_metadata

    fixture = FIXTURE_DIR / "modest-proposal.pdf"
    assert fixture.exists(), "PDF fixture missing"

    metadata = read_metadata(fixture)
    assert metadata.title == "A Modest Proposal"
    assert metadata.authors == ["Jonathan Swift"]


def test_pdf_read_metadata_tags_parsed_from_keywords() -> None:
    """Keywords parse into tags list."""
    from shelvr.formats.pdf import read_metadata

    fixture = FIXTURE_DIR / "modest-proposal.pdf"
    metadata = read_metadata(fixture)

    # Fixture 'keywords' was "public-domain; satire; ireland" → three tags
    assert sorted(metadata.tags) == ["ireland", "public-domain", "satire"]


def test_pdf_read_metadata_description_from_subject() -> None:
    """PDF /Info 'Subject' maps to description."""
    from shelvr.formats.pdf import read_metadata

    fixture = FIXTURE_DIR / "modest-proposal.pdf"
    metadata = read_metadata(fixture)
    assert metadata.description == "Essay, Satire"


def test_pdf_read_metadata_raises_on_nonexistent_file() -> None:
    from shelvr.formats.base import FormatReadError
    from shelvr.formats.pdf import read_metadata

    with pytest.raises(FormatReadError):
        read_metadata(Path("/nonexistent/missing.pdf"))


def test_pdf_read_metadata_raises_on_non_pdf(tmp_path: Path) -> None:
    from shelvr.formats.base import FormatReadError
    from shelvr.formats.pdf import read_metadata

    fake = tmp_path / "not.pdf"
    fake.write_bytes(b"this is not a PDF")

    with pytest.raises(FormatReadError):
        read_metadata(fake)


def test_pdf_extract_cover_returns_png_bytes() -> None:
    """extract_cover returns rendered first-page PNG bytes."""
    from shelvr.formats.pdf import extract_cover

    fixture = FIXTURE_DIR / "modest-proposal.pdf"
    result = extract_cover(fixture)
    assert result is not None
    assert isinstance(result, bytes)
    assert len(result) > 0
    # PNG files start with \x89PNG\r\n\x1a\n
    assert result.startswith(b"\x89PNG\r\n\x1a\n"), "Expected PNG magic bytes at start of cover"


def test_pdf_extensions_tuple() -> None:
    from shelvr.formats.pdf import EXTENSIONS

    assert ".pdf" in EXTENSIONS
    assert isinstance(EXTENSIONS, tuple)

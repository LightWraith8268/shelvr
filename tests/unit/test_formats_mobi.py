"""Tests for the MOBI format reader."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "books"


def test_mobi_read_metadata_returns_title_and_author() -> None:
    """MOBI reader extracts title and author from the PG fixture."""
    from shelvr.formats.mobi import read_metadata

    fixture = FIXTURE_DIR / "modest-proposal.mobi"
    assert fixture.exists(), "MOBI fixture missing"

    metadata = read_metadata(fixture)
    assert metadata.title  # non-empty
    # PG's Modest Proposal should have "Jonathan Swift" as creator
    assert any("swift" in author.lower() for author in metadata.authors), (
        f"Expected a Swift author, got {metadata.authors}"
    )


def test_mobi_read_metadata_raises_on_nonexistent_file() -> None:
    from shelvr.formats.base import FormatReadError
    from shelvr.formats.mobi import read_metadata

    with pytest.raises(FormatReadError):
        read_metadata(Path("/nonexistent/missing.mobi"))


def test_mobi_read_metadata_raises_on_non_mobi(tmp_path: Path) -> None:
    """A file that isn't a MOBI raises FormatReadError."""
    from shelvr.formats.base import FormatReadError
    from shelvr.formats.mobi import read_metadata

    fake = tmp_path / "not.mobi"
    fake.write_bytes(b"this is not a MOBI file")

    with pytest.raises(FormatReadError):
        read_metadata(fake)


def test_mobi_extract_cover_returns_bytes_or_none() -> None:
    """extract_cover returns bytes if a cover is present, else None."""
    from shelvr.formats.mobi import extract_cover

    fixture = FIXTURE_DIR / "modest-proposal.mobi"
    result = extract_cover(fixture)
    assert result is None or (isinstance(result, bytes) and len(result) > 0)


def test_mobi_extensions_tuple_handles_all_variants() -> None:
    from shelvr.formats.mobi import EXTENSIONS

    for ext in (".mobi", ".azw", ".azw3", ".prc"):
        assert ext in EXTENSIONS, f"Expected {ext} in EXTENSIONS"
    assert isinstance(EXTENSIONS, tuple)

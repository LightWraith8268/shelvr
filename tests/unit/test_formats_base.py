"""Tests for the shared Metadata model and FormatReadError exceptions."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_metadata_minimal_construction() -> None:
    """Metadata can be constructed with just a title."""
    from shelvr.formats.base import Metadata

    m = Metadata(title="A Wizard of Earthsea")
    assert m.title == "A Wizard of Earthsea"
    assert m.authors == []
    assert m.series is None
    assert m.series_index is None
    assert m.description is None
    assert m.language is None
    assert m.publisher is None
    assert m.published_date is None
    assert m.isbn is None
    assert m.identifiers == {}
    assert m.tags == []
    assert m.extensions == {}


def test_metadata_full_construction() -> None:
    """Metadata fields all populate correctly."""
    from shelvr.formats.base import Metadata

    m = Metadata(
        title="A Wizard of Earthsea",
        authors=["Ursula K. Le Guin"],
        series="Earthsea",
        series_index=1.0,
        description="First book of Earthsea.",
        language="en",
        publisher="Parnassus Press",
        published_date="1968",
        isbn="9780553262506",
        identifiers={"isbn": "9780553262506", "goodreads": "13642"},
        tags=["fantasy", "coming-of-age"],
        extensions={"dc:rights": "public domain", "custom_field": "value"},
    )
    assert m.title == "A Wizard of Earthsea"
    assert m.authors == ["Ursula K. Le Guin"]
    assert m.series == "Earthsea"
    assert m.series_index == 1.0
    assert m.published_date == "1968"
    assert m.extensions == {"dc:rights": "public domain", "custom_field": "value"}


def test_metadata_title_is_required() -> None:
    """Metadata without a title fails validation."""
    from shelvr.formats.base import Metadata

    with pytest.raises(ValidationError):
        Metadata()  # type: ignore[call-arg]


def test_metadata_extensions_accepts_arbitrary_values() -> None:
    """extensions dict accepts any JSON-serializable value."""
    from shelvr.formats.base import Metadata

    m = Metadata(
        title="Book",
        extensions={
            "string_val": "hello",
            "int_val": 42,
            "list_val": [1, 2, 3],
            "nested": {"a": 1, "b": [2, 3]},
        },
    )
    assert m.extensions["nested"]["b"] == [2, 3]


def test_format_read_error_is_raisable() -> None:
    """FormatReadError can be raised and caught."""
    from shelvr.formats.base import FormatReadError

    with pytest.raises(FormatReadError, match="bad file"):
        raise FormatReadError("bad file")


def test_unsupported_format_error_is_subclass() -> None:
    """UnsupportedFormatError is a FormatReadError subclass."""
    from shelvr.formats.base import FormatReadError, UnsupportedFormatError

    err = UnsupportedFormatError("unknown extension .xyz")
    assert isinstance(err, FormatReadError)


def test_corrupted_file_error_is_subclass() -> None:
    """CorruptedFileError is a FormatReadError subclass."""
    from shelvr.formats.base import CorruptedFileError, FormatReadError

    err = CorruptedFileError("bytes 0..10 not a valid EPUB container")
    assert isinstance(err, FormatReadError)

"""Shared types for the format-reader layer.

Format reader modules live in the same package (`shelvr/formats/*.py`) and each
exposes `read_metadata(path) -> Metadata`, `extract_cover(path) -> bytes | None`,
and an `EXTENSIONS` tuple listing the file extensions they handle.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Metadata(BaseModel):
    """Metadata extracted from an ebook file.

    `extensions` is the escape hatch for any field the format's metadata carries
    that doesn't map cleanly to a first-class attribute above. Format readers
    populate it with whatever they find; Day 3's import pipeline persists it so
    v2's custom-columns feature can consume it. Readers are encouraged but not
    required to populate extensions — leaving it as {} is fine.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1)
    authors: list[str] = Field(default_factory=list)
    series: str | None = None
    series_index: float | None = None
    description: str | None = None
    language: str | None = None
    publisher: str | None = None
    published_date: str | None = None
    isbn: str | None = None
    identifiers: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    extensions: dict[str, Any] = Field(default_factory=dict)


class FormatReadError(Exception):
    """Base class for errors raised by format readers."""


class UnsupportedFormatError(FormatReadError):
    """Raised when the file's format is not supported by any reader."""


class CorruptedFileError(FormatReadError):
    """Raised when a file appears to be the right format but can't be parsed."""

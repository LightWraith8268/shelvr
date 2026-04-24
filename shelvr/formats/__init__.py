"""Shared types for format readers.

Format reader implementations live as built-in plugins under
``shelvr.plugins.builtin.*``. This package keeps the shared Metadata model,
FormatImportResult, and the FormatReadError hierarchy that plugins raise.
"""

from __future__ import annotations

from shelvr.formats.base import (
    CorruptedFileError,
    FormatImportResult,
    FormatReadError,
    Metadata,
    UnsupportedFormatError,
)

__all__ = [
    "CorruptedFileError",
    "FormatImportResult",
    "FormatReadError",
    "Metadata",
    "UnsupportedFormatError",
]

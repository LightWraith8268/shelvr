"""Format reader registry.

Each `shelvr.formats.<format>` submodule exposes:
    - EXTENSIONS: tuple[str, ...]  — extensions handled (include the leading dot)
    - read_metadata(path: Path) -> Metadata
    - extract_cover(path: Path) -> bytes | None

Use `get_reader_for_path(path)` to dispatch to the right module by extension.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

from shelvr.formats import epub, mobi, pdf
from shelvr.formats.base import (
    CorruptedFileError,
    FormatReadError,
    Metadata,
    UnsupportedFormatError,
)

_READERS: tuple[ModuleType, ...] = (epub, pdf, mobi)

_EXTENSION_MAP: dict[str, ModuleType] = {
    ext.lower(): reader for reader in _READERS for ext in reader.EXTENSIONS
}


def get_reader_for_path(path: Path) -> ModuleType:
    """Return the format reader module for the given path's extension.

    Raises:
        UnsupportedFormatError: If no registered reader handles this extension.
    """
    ext = path.suffix.lower()
    reader = _EXTENSION_MAP.get(ext)
    if reader is None:
        raise UnsupportedFormatError(f"No format reader registered for {ext!r}")
    return reader


__all__ = [
    "CorruptedFileError",
    "FormatReadError",
    "Metadata",
    "UnsupportedFormatError",
    "epub",
    "get_reader_for_path",
    "mobi",
    "pdf",
]

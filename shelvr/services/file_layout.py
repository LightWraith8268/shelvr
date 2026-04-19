"""Filename and library-path sanitization helpers.

`sanitize_segment` scrubs a single path segment (a directory or file stem)
of characters and patterns that are invalid on Windows (the most-restrictive
of our target OSes). `compute_target_path` assembles a full file path under
the configured library root using a consistent layout:

    <library_root>/<sanitized primary author>/<sanitized title>/<sanitized title>.<ext>

Books with no declared author land under 'Unknown Author'.
"""

from __future__ import annotations

from pathlib import Path

_FORBIDDEN_CHARS = '/\\:*?"<>|'
_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *{f"COM{i}" for i in range(1, 10)},
        *{f"LPT{i}" for i in range(1, 10)},
    }
)
_MAX_SEGMENT_LEN = 100


def sanitize_segment(raw: str) -> str:
    """Scrub a single path segment (a directory name or file stem).

    - Replaces each of ``/\\:*?"<>|`` with ``_``
    - Strips trailing dots and whitespace (Windows disallows them)
    - Appends ``_`` to reserved names (CON, PRN, COM1, LPT9, ...)
    - Truncates to ``_MAX_SEGMENT_LEN`` characters
    - Returns ``_`` if the result would be empty
    """
    cleaned = "".join("_" if c in _FORBIDDEN_CHARS else c for c in raw)
    while cleaned and cleaned[-1] in " .":
        cleaned = cleaned[:-1]
    cleaned = cleaned.strip()
    # If the original segment was composed entirely of forbidden chars,
    # the result is a run of underscores — collapse to the single-char
    # placeholder so naming stays predictable.
    if not cleaned or set(cleaned) == {"_"}:
        return "_"
    if cleaned.upper() in _RESERVED_NAMES:
        cleaned = cleaned + "_"
    if len(cleaned) > _MAX_SEGMENT_LEN:
        cleaned = cleaned[:_MAX_SEGMENT_LEN]
    return cleaned


def compute_target_path(
    library_root: Path,
    primary_author: str | None,
    title: str,
    extension: str,
) -> Path:
    """Compute the canonical target path for an imported book file.

    Layout:
        <library_root>/<author>/<title>/<title>.<ext>

    Args:
        library_root: The user-configured library directory.
        primary_author: Author name; falls back to 'Unknown Author' when None
            or empty.
        title: Book title.
        extension: File extension, with or without the leading dot.

    Returns:
        An absolute path. The parent directory does NOT have to exist — the
        importer service creates it on first write.
    """
    author_segment = sanitize_segment(primary_author or "Unknown Author")
    title_segment = sanitize_segment(title)
    ext = extension if extension.startswith(".") else f".{extension}"
    ext = ext.lower()
    filename = f"{title_segment}{ext}"
    return library_root / author_segment / title_segment / filename

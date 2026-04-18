"""PDF format reader (pymupdf-backed).

For PDFs, 'cover' is the rendered first page as a PNG — there's no native cover
concept the way EPUB has. The rendered-page approach matches what Calibre does.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shelvr.formats.base import CorruptedFileError, FormatReadError, Metadata

EXTENSIONS: tuple[str, ...] = (".pdf",)


def read_metadata(path: Path) -> Metadata:
    """Extract metadata from a PDF file.

    Reads the PDF's /Info dictionary. XMP metadata support could be layered on
    later; pymupdf exposes XMP via `doc.xref_xml_metadata()` but /Info covers
    the common case.

    Raises:
        FormatReadError: If the file doesn't exist or isn't a valid PDF.
    """
    if not path.exists():
        raise FormatReadError(f"PDF file not found: {path}")

    doc = _open_pdf(path)
    try:
        info = doc.metadata or {}
        title = (info.get("title") or "").strip() or path.stem
        authors = _parse_authors(info.get("author"))
        description = (info.get("subject") or "").strip() or None
        publisher = (info.get("producer") or "").strip() or None
        published_date = _parse_pdf_date(info.get("creationDate"))
        tags = _parse_keywords(info.get("keywords"))
        extensions = _collect_extensions(info, publisher)

        return Metadata(
            title=title,
            authors=authors,
            description=description,
            publisher=publisher,
            published_date=published_date,
            tags=tags,
            extensions=extensions,
        )
    finally:
        doc.close()


def extract_cover(path: Path) -> bytes | None:
    """Render the first page as a PNG and return its bytes.

    Returns None if the PDF has no pages.

    Raises:
        FormatReadError: If the file doesn't exist or isn't a valid PDF.
    """
    if not path.exists():
        raise FormatReadError(f"PDF file not found: {path}")

    doc = _open_pdf(path)
    try:
        if doc.page_count == 0:
            return None
        page = doc.load_page(0)
        pixmap = page.get_pixmap(dpi=150)
        return bytes(pixmap.tobytes("png"))
    finally:
        doc.close()


def _open_pdf(path: Path) -> Any:
    """Open a PDF, wrapping underlying errors in CorruptedFileError."""
    try:
        import fitz  # pymupdf

        return fitz.open(str(path))
    except Exception as exc:
        raise CorruptedFileError(f"Failed to open PDF {path}: {exc}") from exc


def _parse_authors(raw: str | None) -> list[str]:
    """Split a PDF /Info 'Author' string into individual authors."""
    if not raw:
        return []
    raw = raw.strip()
    if not raw:
        return []
    for sep in (" and ", ", ", ";"):
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep) if p.strip()]
            if parts:
                return parts
    return [raw]


def _parse_keywords(raw: str | None) -> list[str]:
    """Split a PDF /Info 'Keywords' field on semicolons or commas."""
    if not raw:
        return []
    raw = raw.strip()
    if not raw:
        return []
    for sep in (";", ","):
        if sep in raw:
            return [k.strip() for k in raw.split(sep) if k.strip()]
    return [raw]


def _parse_pdf_date(raw: str | None) -> str | None:
    """Extract a displayable YYYY-MM-DD from a PDF /Info date string.

    PDF dates look like "D:20230415120000+00'00'" — strip the D: prefix and
    return the ISO date when parseable, else the raw value.
    """
    if not raw:
        return None
    cleaned = raw[2:] if raw.startswith("D:") else raw
    digits = cleaned[:14]
    if len(digits) >= 8 and digits[:8].isdigit():
        yyyy, mm, dd = digits[:4], digits[4:6], digits[6:8]
        return f"{yyyy}-{mm}-{dd}"
    return cleaned or None


def _collect_extensions(info: dict[str, Any], publisher: str | None) -> dict[str, Any]:
    """Surface non-first-class /Info fields into extensions."""
    known = {
        "title",
        "author",
        "subject",
        "producer",
        "keywords",
        "creationDate",
    }
    extensions: dict[str, Any] = {}
    for key, value in info.items():
        if not value or key in known:
            continue
        extensions[f"pdf:info:{key}"] = value
    # 'creator' shouldn't overwrite 'producer' which we already used for publisher,
    # so record it separately if distinct.
    creator = (info.get("creator") or "").strip()
    if creator and creator != publisher:
        extensions["pdf:info:creator"] = creator
    return extensions

"""Built-in PDF format reader plugin."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shelvr.formats.base import CorruptedFileError, FormatImportResult, Metadata
from shelvr.plugins.base import Plugin

HANDLED_EXTENSIONS: frozenset[str] = frozenset({".pdf"})


class PdfFormatPlugin(Plugin):
    """Reads metadata and renders the first page as a cover image."""

    id = "builtin.pdf"
    version = "1.0.0"

    async def on_format_import(self, path: Path, extension: str) -> FormatImportResult | None:
        if extension.lower() not in HANDLED_EXTENSIONS:
            return None
        # pymupdf is synchronous and does blocking IO internally; a brief
        # stat() here is negligible next to that. Host is free to offload the
        # whole call to a worker thread if this becomes a hotspot.
        if not path.exists():  # noqa: ASYNC240
            self.ctx.logger.warning("pdf_file_missing", path=str(path))
            return None

        doc = _open_pdf(path)
        try:
            metadata = _extract_metadata(doc, path)
            cover_bytes = _extract_cover(doc)
        finally:
            doc.close()
        return FormatImportResult(metadata=metadata, cover_bytes=cover_bytes)


def _open_pdf(path: Path) -> Any:
    try:
        import fitz

        return fitz.open(str(path))
    except Exception as exc:
        raise CorruptedFileError(f"Failed to open PDF {path}: {exc}") from exc


def _extract_metadata(doc: Any, path: Path) -> Metadata:
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


def _extract_cover(doc: Any) -> bytes | None:
    if doc.page_count == 0:
        return None
    page = doc.load_page(0)
    pixmap = page.get_pixmap(dpi=150)
    return bytes(pixmap.tobytes("png"))


def _parse_authors(raw: str | None) -> list[str]:
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
    if not raw:
        return None
    cleaned = raw[2:] if raw.startswith("D:") else raw
    digits = cleaned[:14]
    if len(digits) >= 8 and digits[:8].isdigit():
        yyyy, mm, dd = digits[:4], digits[4:6], digits[6:8]
        return f"{yyyy}-{mm}-{dd}"
    return cleaned or None


def _collect_extensions(info: dict[str, Any], publisher: str | None) -> dict[str, Any]:
    known = {"title", "author", "subject", "producer", "keywords", "creationDate"}
    extensions: dict[str, Any] = {}
    for key, value in info.items():
        if not value or key in known:
            continue
        extensions[f"pdf:info:{key}"] = value
    creator = (info.get("creator") or "").strip()
    if creator and creator != publisher:
        extensions["pdf:info:creator"] = creator
    return extensions

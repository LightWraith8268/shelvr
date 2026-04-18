"""EPUB format reader (ebooklib-backed)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shelvr.formats.base import CorruptedFileError, FormatReadError, Metadata

EXTENSIONS: tuple[str, ...] = (".epub",)


def read_metadata(path: Path) -> Metadata:
    """Extract metadata from an EPUB file.

    Raises:
        FormatReadError: If the file does not exist or cannot be parsed.
    """
    if not path.exists():
        raise FormatReadError(f"EPUB file not found: {path}")

    book = _open_epub(path)

    title = _first_text(book, "DC", "title") or path.stem
    authors = _all_text(book, "DC", "creator")
    description = _first_text(book, "DC", "description")
    language = _first_text(book, "DC", "language")
    publisher = _first_text(book, "DC", "publisher")
    published_date = _first_text(book, "DC", "date")
    identifiers = _extract_identifiers(book)
    isbn = identifiers.get("isbn")
    tags = _all_text(book, "DC", "subject")
    extensions = _extract_extensions(book)

    return Metadata(
        title=title,
        authors=authors,
        description=description,
        language=language,
        publisher=publisher,
        published_date=published_date,
        isbn=isbn,
        identifiers=identifiers,
        tags=tags,
        extensions=extensions,
    )


def extract_cover(path: Path) -> bytes | None:
    """Return the EPUB's cover image bytes, or None if the file has no cover.

    Raises:
        FormatReadError: If the file does not exist or cannot be parsed.
    """
    if not path.exists():
        raise FormatReadError(f"EPUB file not found: {path}")

    import ebooklib

    book = _open_epub(path)

    for item in book.get_items_of_type(ebooklib.ITEM_COVER):
        content = item.get_content()
        if content:
            return bytes(content)

    # Fallback: sometimes the cover is classified as a plain IMAGE with 'cover'
    # in its filename (older EPUBs and some PG variants).
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        name = (getattr(item, "file_name", "") or "").lower()
        if "cover" in name:
            content = item.get_content()
            if content:
                return bytes(content)

    return None


def _open_epub(path: Path) -> Any:
    """Open an EPUB, wrapping any underlying error in CorruptedFileError."""
    try:
        from ebooklib import epub

        return epub.read_epub(str(path))
    except Exception as exc:
        raise CorruptedFileError(f"Failed to read EPUB {path}: {exc}") from exc


def _first_text(book: Any, namespace: str, tag: str) -> str | None:
    """Return the first text value for a given DC/OPF metadata tag, or None."""
    entries = book.get_metadata(namespace, tag)
    if not entries:
        return None
    value = entries[0][0] if entries[0] else None
    return value.strip() if isinstance(value, str) and value.strip() else None


def _all_text(book: Any, namespace: str, tag: str) -> list[str]:
    """Return all text values for a given DC/OPF metadata tag, in declared order."""
    return [
        entry[0].strip()
        for entry in (book.get_metadata(namespace, tag) or [])
        if entry and isinstance(entry[0], str) and entry[0].strip()
    ]


def _extract_identifiers(book: Any) -> dict[str, str]:
    """Map DC:identifier entries to a {scheme: value} dict.

    If a DC:identifier lacks an explicit scheme attribute but its value starts
    with 'urn:isbn:' we still classify it as ISBN.
    """
    result: dict[str, str] = {}
    for entry in book.get_metadata("DC", "identifier") or []:
        value = entry[0] or ""
        if not value:
            continue
        attrs = entry[1] if len(entry) > 1 and entry[1] else {}
        scheme = (attrs.get("scheme") or "").lower()
        if not scheme and value.lower().startswith("urn:isbn:"):
            scheme = "isbn"
            value = value[len("urn:isbn:") :].replace("-", "").strip()
        scheme = scheme or "id"
        result[scheme] = value
    return result


def _extract_extensions(book: Any) -> dict[str, Any]:
    """Collect DC/OPF metadata fields we don't have first-class homes for."""
    known_dc = {
        "title",
        "creator",
        "description",
        "language",
        "publisher",
        "date",
        "identifier",
        "subject",
    }
    extensions: dict[str, Any] = {}
    # book.metadata is an internal dict: {namespace: {tag: [(value, attrs), ...]}}
    # We treat it as read-only.
    metadata_raw = getattr(book, "metadata", None) or {}
    for ns, tags in metadata_raw.items():
        if not isinstance(tags, dict):
            continue
        for tag_name, entries in tags.items():
            if ns == "DC" and tag_name in known_dc:
                continue
            if not entries:
                continue
            values = [entry[0] for entry in entries if entry and entry[0]]
            if not values:
                continue
            ns_prefix = ns.lower() if ns else "x"
            key = f"{ns_prefix}:{tag_name}" if tag_name else ns_prefix
            extensions[key] = values if len(values) > 1 else values[0]
    return extensions

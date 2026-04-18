"""MOBI / AZW / AZW3 format reader.

Strategy: use the `mobi` pip package to unpack the file to a temp directory,
which produces an OPF manifest + associated resources. Parse the OPF directly
with `xml.etree.ElementTree` to avoid ebooklib's EPUB-specific assumptions.

Known limitation: the `mobi` package's maintenance is uneven. If a real file
fails to unpack, escalate to Calibre's `ebook-meta` CLI via the v2 Calibre-bridge
plugin. For now we accept the limitation and surface failures as
CorruptedFileError.
"""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from shelvr.formats.base import CorruptedFileError, FormatReadError, Metadata

EXTENSIONS: tuple[str, ...] = (".mobi", ".azw", ".azw3", ".prc")


def read_metadata(path: Path) -> Metadata:
    """Extract metadata from a MOBI/AZW/PRC file.

    Raises:
        FormatReadError: If the file doesn't exist or cannot be parsed.
    """
    if not path.exists():
        raise FormatReadError(f"MOBI file not found: {path}")

    tempdir = _extract_to_temp(path)
    try:
        opf_path = _find_opf(Path(tempdir), path)
        return _parse_opf(opf_path)
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def extract_cover(path: Path) -> bytes | None:
    """Return the MOBI's cover image bytes, or None if no cover is present."""
    if not path.exists():
        raise FormatReadError(f"MOBI file not found: {path}")

    tempdir = _extract_to_temp(path)
    try:
        tempdir_path = Path(tempdir)
        # Prefer canonical 'cover.<ext>' in the temp root
        for name in ("cover.jpeg", "cover.jpg", "cover.png", "cover.gif"):
            candidate = tempdir_path / name
            if candidate.exists():
                return candidate.read_bytes()
        # Fallback: scan recursively for any image whose name contains 'cover'
        for item in tempdir_path.rglob("*"):
            if (
                item.is_file()
                and "cover" in item.name.lower()
                and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif"}
            ):
                return item.read_bytes()
        return None
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def _extract_to_temp(path: Path) -> str:
    """Unpack a MOBI via the `mobi` pip package; return the temp directory.

    Wraps every underlying exception in CorruptedFileError so callers can catch
    a single exception type.
    """
    try:
        import mobi as mobi_pkg

        tempdir, _inner = mobi_pkg.extract(str(path))
        return str(tempdir)
    except Exception as exc:
        raise CorruptedFileError(f"Failed to unpack MOBI {path}: {exc}") from exc


def _find_opf(tempdir: Path, original_path: Path) -> Path:
    """Locate the OPF manifest inside an unpacked MOBI temp directory."""
    opfs = list(tempdir.rglob("*.opf"))
    if not opfs:
        raise CorruptedFileError(f"MOBI {original_path} unpacked without an OPF manifest")
    return opfs[0]


def _parse_opf(opf_path: Path) -> Metadata:
    """Parse an OPF metadata file into a Metadata instance."""
    try:
        tree = ET.parse(opf_path)
    except Exception as exc:
        raise CorruptedFileError(f"Failed to parse OPF {opf_path}: {exc}") from exc

    metadata_el = _find_metadata_element(tree.getroot())

    title: str | None = None
    authors: list[str] = []
    description: str | None = None
    language: str | None = None
    publisher: str | None = None
    published_date: str | None = None
    isbn: str | None = None
    identifiers: dict[str, str] = {}
    tags: list[str] = []
    extensions: dict[str, Any] = {}

    if metadata_el is not None:
        for child in metadata_el:
            name = _local_name(child.tag)
            text = (child.text or "").strip()
            if not text:
                continue
            if name == "title":
                title = text if title is None else title  # keep the first
            elif name == "creator":
                authors.append(text)
            elif name == "description":
                description = text
            elif name == "language":
                language = text
            elif name == "publisher":
                publisher = text
            elif name == "date":
                published_date = text
            elif name == "subject":
                tags.append(text)
            elif name == "identifier":
                scheme = _identifier_scheme(child).lower()
                value = text
                if scheme == "isbn" or value.lower().startswith("urn:isbn:"):
                    stripped = value
                    if stripped.lower().startswith("urn:isbn:"):
                        stripped = stripped[len("urn:isbn:") :]
                    stripped = stripped.replace("-", "").strip()
                    if stripped:
                        isbn = stripped
                        identifiers["isbn"] = stripped
                else:
                    identifiers[scheme or "id"] = value
            else:
                _accumulate_extension(extensions, f"opf:{name}", text)

    return Metadata(
        title=title or opf_path.stem,
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


def _find_metadata_element(root: ET.Element) -> ET.Element | None:
    """Return the <metadata> child of the OPF root, ignoring namespaces."""
    for child in root:
        if _local_name(child.tag) == "metadata":
            return child
    return None


def _local_name(tag: str) -> str:
    """Return the local-name portion of an XML tag (strip namespace)."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _identifier_scheme(el: ET.Element) -> str:
    """Return the OPF scheme attribute from an identifier element, or ''."""
    for attr_name, attr_value in el.attrib.items():
        if _local_name(attr_name) == "scheme":
            return attr_value
    return ""


def _accumulate_extension(extensions: dict[str, Any], key: str, value: str) -> None:
    """Add a value to an extensions-dict slot, handling repeats as lists."""
    existing = extensions.get(key)
    if existing is None:
        extensions[key] = value
    elif isinstance(existing, list):
        existing.append(value)
    else:
        extensions[key] = [existing, value]

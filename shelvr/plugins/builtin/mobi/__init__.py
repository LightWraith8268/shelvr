"""Built-in MOBI/AZW/AZW3/PRC format reader plugin."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from shelvr.formats.base import CorruptedFileError, FormatImportResult, Metadata
from shelvr.plugins.base import Plugin

HANDLED_EXTENSIONS: frozenset[str] = frozenset({".mobi", ".azw", ".azw3", ".prc"})


class MobiFormatPlugin(Plugin):
    """Reads metadata and cover from MOBI/AZW/AZW3/PRC files.

    Uses the ``mobi`` pip package to unpack to a temp dir, then parses the
    resulting OPF manifest directly.
    """

    id = "builtin.mobi"
    version = "1.0.0"

    async def on_format_import(self, path: Path, extension: str) -> FormatImportResult | None:
        if extension.lower() not in HANDLED_EXTENSIONS:
            return None
        if not path.exists():  # noqa: ASYNC240
            self.ctx.logger.warning("mobi_file_missing", path=str(path))
            return None

        tempdir = _extract_to_temp(path)
        try:
            tempdir_path = Path(tempdir)
            opf_path = _find_opf(tempdir_path, path)
            metadata = _parse_opf(opf_path)
            cover_bytes = _find_cover(tempdir_path)
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)
        return FormatImportResult(metadata=metadata, cover_bytes=cover_bytes)


def _extract_to_temp(path: Path) -> str:
    try:
        import mobi as mobi_pkg

        tempdir, _inner = mobi_pkg.extract(str(path))
        return str(tempdir)
    except Exception as exc:
        raise CorruptedFileError(f"Failed to unpack MOBI {path}: {exc}") from exc


def _find_opf(tempdir: Path, original_path: Path) -> Path:
    opfs = list(tempdir.rglob("*.opf"))
    if not opfs:
        raise CorruptedFileError(f"MOBI {original_path} unpacked without an OPF manifest")
    return opfs[0]


def _find_cover(tempdir: Path) -> bytes | None:
    for name in ("cover.jpeg", "cover.jpg", "cover.png", "cover.gif"):
        candidate = tempdir / name
        if candidate.exists():
            return candidate.read_bytes()
    for item in tempdir.rglob("*"):
        if (
            item.is_file()
            and "cover" in item.name.lower()
            and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif"}
        ):
            return item.read_bytes()
    return None


def _parse_opf(opf_path: Path) -> Metadata:
    try:
        tree = ET.parse(opf_path)
    except Exception as exc:
        raise CorruptedFileError(f"Failed to parse OPF {opf_path}: {exc}") from exc

    root = tree.getroot()
    metadata_el: ET.Element | None = None
    for child in root:
        if _local_name(child.tag) == "metadata":
            metadata_el = child
            break

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
                title = text if title is None else title
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


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _identifier_scheme(el: ET.Element) -> str:
    for attr_name, attr_value in el.attrib.items():
        if _local_name(attr_name) == "scheme":
            return attr_value
    return ""


def _accumulate_extension(extensions: dict[str, Any], key: str, value: str) -> None:
    existing = extensions.get(key)
    if existing is None:
        extensions[key] = value
    elif isinstance(existing, list):
        existing.append(value)
    else:
        extensions[key] = [existing, value]

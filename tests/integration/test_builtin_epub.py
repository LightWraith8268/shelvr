"""Tests for the built-in EPUB format plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "books"
BUILTIN_DIR = Path(__file__).parent.parent.parent / "shelvr" / "plugins" / "builtin"


def test_epub_plugin_manifest_parses() -> None:
    from shelvr.plugins.manifest import load_manifest

    manifest = load_manifest(BUILTIN_DIR / "epub" / "plugin.toml")
    assert manifest.id == "builtin.epub"
    assert manifest.api_version == "1"
    assert manifest.hooks.get("on_format_import") is True


def test_epub_plugin_loads() -> None:
    from shelvr.plugins.loader import PluginLoader

    loader = PluginLoader(BUILTIN_DIR)
    loaded = loader.discover()
    ids = {entry.manifest.id for entry in loaded}
    assert "builtin.epub" in ids


@pytest.mark.asyncio
async def test_epub_plugin_extracts_metadata_and_cover() -> None:
    """on_format_import returns FormatImportResult with real metadata."""
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    loader = PluginLoader(BUILTIN_DIR)
    registry = PluginRegistry()
    for entry in loader.discover():
        if entry.manifest.id == "builtin.epub":
            registry.register(entry)

    fixture = FIXTURE_DIR / "modest-proposal.epub"
    result = await registry.fire_handler("on_format_import", path=fixture, extension=".epub")

    assert result is not None
    assert result.metadata.title
    assert any("swift" in author.lower() for author in result.metadata.authors)
    assert result.cover_bytes is not None
    assert len(result.cover_bytes) > 0


@pytest.mark.asyncio
async def test_epub_plugin_returns_none_for_non_epub() -> None:
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    loader = PluginLoader(BUILTIN_DIR)
    registry = PluginRegistry()
    for entry in loader.discover():
        if entry.manifest.id == "builtin.epub":
            registry.register(entry)

    result = await registry.fire_handler(
        "on_format_import", path=Path("fake.pdf"), extension=".pdf"
    )
    assert result is None


@pytest.mark.asyncio
async def test_epub_plugin_wraps_parse_errors_as_none(tmp_path: Path) -> None:
    """A corrupted EPUB produces None (handler isolation), not a raise."""
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    loader = PluginLoader(BUILTIN_DIR)
    registry = PluginRegistry()
    for entry in loader.discover():
        if entry.manifest.id == "builtin.epub":
            registry.register(entry)

    corrupted = tmp_path / "corrupted.epub"
    corrupted.write_bytes(b"this is not an EPUB")

    result = await registry.fire_handler("on_format_import", path=corrupted, extension=".epub")
    assert result is None

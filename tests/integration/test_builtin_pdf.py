"""Tests for the built-in PDF format plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "books"
BUILTIN_DIR = Path(__file__).parent.parent.parent / "shelvr" / "plugins" / "builtin"


def test_pdf_plugin_manifest_parses() -> None:
    from shelvr.plugins.manifest import load_manifest

    manifest = load_manifest(BUILTIN_DIR / "pdf" / "plugin.toml")
    assert manifest.id == "builtin.pdf"


def test_pdf_plugin_loads() -> None:
    from shelvr.plugins.loader import PluginLoader

    loader = PluginLoader(BUILTIN_DIR)
    loaded = loader.discover()
    ids = {entry.manifest.id for entry in loaded}
    assert "builtin.pdf" in ids


@pytest.mark.asyncio
async def test_pdf_plugin_extracts_metadata_and_cover() -> None:
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    loader = PluginLoader(BUILTIN_DIR)
    registry = PluginRegistry()
    for entry in loader.discover():
        if entry.manifest.id == "builtin.pdf":
            registry.register(entry)

    fixture = FIXTURE_DIR / "modest-proposal.pdf"
    result = await registry.fire_handler("on_format_import", path=fixture, extension=".pdf")

    assert result is not None
    assert result.metadata.title == "A Modest Proposal"
    assert result.metadata.authors == ["Jonathan Swift"]
    assert sorted(result.metadata.tags) == ["ireland", "public-domain", "satire"]
    # Cover is the rendered first page — PNG bytes
    assert result.cover_bytes is not None
    assert result.cover_bytes.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.asyncio
async def test_pdf_plugin_returns_none_for_non_pdf() -> None:
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    loader = PluginLoader(BUILTIN_DIR)
    registry = PluginRegistry()
    for entry in loader.discover():
        if entry.manifest.id == "builtin.pdf":
            registry.register(entry)

    result = await registry.fire_handler(
        "on_format_import", path=Path("fake.epub"), extension=".epub"
    )
    assert result is None

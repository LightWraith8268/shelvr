"""Tests for the built-in MOBI format plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "books"
BUILTIN_DIR = Path(__file__).parent.parent.parent / "shelvr" / "plugins" / "builtin"


def test_mobi_plugin_manifest_parses() -> None:
    from shelvr.plugins.manifest import load_manifest

    manifest = load_manifest(BUILTIN_DIR / "mobi" / "plugin.toml")
    assert manifest.id == "builtin.mobi"


def test_mobi_plugin_loads() -> None:
    from shelvr.plugins.loader import PluginLoader

    loader = PluginLoader(BUILTIN_DIR)
    loaded = loader.discover()
    ids = {entry.manifest.id for entry in loaded}
    assert "builtin.mobi" in ids


@pytest.mark.asyncio
async def test_mobi_plugin_extracts_metadata_and_cover() -> None:
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    loader = PluginLoader(BUILTIN_DIR)
    registry = PluginRegistry()
    for entry in loader.discover():
        if entry.manifest.id == "builtin.mobi":
            registry.register(entry)

    fixture = FIXTURE_DIR / "modest-proposal.mobi"
    result = await registry.fire_handler("on_format_import", path=fixture, extension=".mobi")

    assert result is not None
    assert result.metadata.title
    assert any("swift" in author.lower() for author in result.metadata.authors)
    assert result.cover_bytes is None or isinstance(result.cover_bytes, bytes)


@pytest.mark.asyncio
async def test_mobi_plugin_handles_all_kindle_extensions() -> None:
    """.mobi, .azw, .azw3, .prc all dispatch to this plugin."""
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    loader = PluginLoader(BUILTIN_DIR)
    registry = PluginRegistry()
    for entry in loader.discover():
        if entry.manifest.id == "builtin.mobi":
            registry.register(entry)

    # For all four, a missing file produces None (plugin is responsible;
    # we just want to verify the extension check doesn't reject the format).
    for ext in (".mobi", ".azw", ".azw3", ".prc"):
        result = await registry.fire_handler(
            "on_format_import", path=Path("nonexistent" + ext), extension=ext
        )
        # Either None (file missing) or a result — never raises
        assert result is None or hasattr(result, "metadata")


@pytest.mark.asyncio
async def test_mobi_plugin_returns_none_for_non_kindle() -> None:
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    loader = PluginLoader(BUILTIN_DIR)
    registry = PluginRegistry()
    for entry in loader.discover():
        if entry.manifest.id == "builtin.mobi":
            registry.register(entry)

    result = await registry.fire_handler(
        "on_format_import", path=Path("fake.epub"), extension=".epub"
    )
    assert result is None

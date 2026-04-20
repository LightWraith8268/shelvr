"""End-to-end test: hello_world reference plugin loads and fires."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_PLUGINS_DIR = Path(__file__).parent.parent.parent / "plugins"


def test_hello_world_manifest_parses() -> None:
    """The reference plugin's manifest is valid."""
    from shelvr.plugins.manifest import load_manifest

    manifest = load_manifest(REPO_PLUGINS_DIR / "hello_world" / "plugin.toml")
    assert manifest.id == "hello_world"
    assert manifest.api_version == "1"
    assert manifest.hooks.get("on_book_added") is True


def test_hello_world_loads_via_loader() -> None:
    """The loader discovers and instantiates hello_world."""
    from shelvr.plugins.loader import PluginLoader

    loader = PluginLoader(REPO_PLUGINS_DIR)
    loaded = loader.discover()
    ids = {entry.manifest.id for entry in loaded}
    assert "hello_world" in ids


@pytest.mark.asyncio
async def test_hello_world_fires_on_book_added() -> None:
    """Firing on_book_added against the hello_world plugin runs without error."""
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    loader = PluginLoader(REPO_PLUGINS_DIR)
    registry = PluginRegistry()
    for entry in loader.discover():
        if entry.manifest.id == "hello_world":
            registry.register(entry)

    class FakeBook:
        title = "Test Book"

    # Should not raise
    await registry.fire_event("on_book_added", book=FakeBook())

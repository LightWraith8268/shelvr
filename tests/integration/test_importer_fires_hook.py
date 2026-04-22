"""Integration test: importer fires on_book_added when plugins are loaded."""

from __future__ import annotations

from pathlib import Path

import pytest
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "books"
BUILTIN_DIR = Path(__file__).parent.parent.parent / "shelvr" / "plugins" / "builtin"


@pytest.mark.asyncio
async def test_importer_fires_on_book_added(session: AsyncSession, library_path: Path) -> None:
    """Importing a book with a registry attached fires on_book_added."""
    from shelvr.plugins.base import Plugin
    from shelvr.plugins.context import PluginContext
    from shelvr.plugins.loader import LoadedPlugin, PluginLoader
    from shelvr.plugins.manifest import PluginManifest
    from shelvr.plugins.registry import PluginRegistry
    from shelvr.services.importer import import_file

    seen_titles: list[str] = []

    class CapturingPlugin(Plugin):
        id = "capture"
        version = "1.0.0"

        async def on_book_added(self, book) -> None:
            seen_titles.append(book.title)

    plugin_instance = CapturingPlugin(
        PluginContext(
            plugin_id="capture",
            logger=structlog.get_logger("plugin.capture"),
            config={},
        )
    )
    manifest = PluginManifest(id="capture", name="Capture", version="1.0.0", api_version="1")

    registry = PluginRegistry()
    # Load built-in plugins so on_format_import has a handler
    for loaded in PluginLoader(BUILTIN_DIR).discover():
        registry.register(loaded)
    # Add our capturing plugin
    registry.register(LoadedPlugin(manifest=manifest, instance=plugin_instance))

    epub_bytes = (FIXTURE_DIR / "modest-proposal.epub").read_bytes()
    book = await import_file(
        file_bytes=epub_bytes,
        original_filename="modest-proposal.epub",
        library_root=library_path,
        session=session,
        plugin_registry=registry,
    )
    await session.flush()

    assert book.id is not None
    assert seen_titles == [book.title]

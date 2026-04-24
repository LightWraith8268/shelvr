"""Tests for the plugin registry and event dispatch."""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_plugin(plugin_dir: Path, plugin_id: str, body: str) -> None:
    """Write a plugin with custom __init__.py body (for capturing behavior)."""
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.toml").write_text(
        f"""
[plugin]
id = "{plugin_id}"
name = "Plugin"
version = "1.0.0"
api_version = "1"
""",
        encoding="utf-8",
    )
    (plugin_dir / "__init__.py").write_text(body, encoding="utf-8")


@pytest.mark.asyncio
async def test_registry_register_and_get() -> None:
    import structlog

    from shelvr.plugins.base import Plugin
    from shelvr.plugins.context import PluginContext
    from shelvr.plugins.loader import LoadedPlugin
    from shelvr.plugins.manifest import PluginManifest
    from shelvr.plugins.registry import PluginRegistry

    class P(Plugin):
        id = "p"
        version = "1.0.0"

    instance = P(
        PluginContext(
            plugin_id="p",
            logger=structlog.get_logger("plugin.p"),
            config={},
        )
    )
    manifest = PluginManifest(id="p", name="P", version="1.0.0", api_version="1")
    loaded = LoadedPlugin(manifest=manifest, instance=instance)

    registry = PluginRegistry()
    registry.register(loaded)

    assert registry.get("p") is loaded
    assert list(registry.all()) == [loaded]
    assert registry.get("nonexistent") is None


@pytest.mark.asyncio
async def test_registry_fire_event_calls_subscribers(tmp_path: Path) -> None:
    """fire_event invokes the matching method on each loaded plugin."""
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    _write_plugin(
        tmp_path / "capturer",
        "capturer",
        """
from shelvr.plugins.base import Plugin


class CapturingPlugin(Plugin):
    id = "capturer"
    version = "1.0.0"

    seen: list = []

    async def on_book_added(self, book) -> None:
        type(self).seen.append(book)
""",
    )

    loader = PluginLoader(tmp_path)
    loaded = loader.discover()
    assert len(loaded) == 1

    registry = PluginRegistry()
    for entry in loaded:
        registry.register(entry)

    sentinel = object()
    await registry.fire_event("on_book_added", book=sentinel)

    instance_class = type(loaded[0].instance)
    assert instance_class.seen == [sentinel]


@pytest.mark.asyncio
async def test_registry_fire_event_skips_plugins_without_method(tmp_path: Path) -> None:
    """A plugin that doesn't define on_xyz is silently skipped (default no-op fires harmlessly)."""
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    _write_plugin(
        tmp_path / "noop",
        "noop",
        """
from shelvr.plugins.base import Plugin


class NoopPlugin(Plugin):
    id = "noop"
    version = "1.0.0"
""",
    )

    loader = PluginLoader(tmp_path)
    registry = PluginRegistry()
    for entry in loader.discover():
        registry.register(entry)

    # Default on_book_added is a no-op coroutine; firing should not raise.
    await registry.fire_event("on_book_added", book=object())


@pytest.mark.asyncio
async def test_registry_fire_event_isolates_plugin_failures(tmp_path: Path) -> None:
    """One plugin raising during a hook does not stop others from running."""
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    _write_plugin(
        tmp_path / "raiser",
        "raiser",
        """
from shelvr.plugins.base import Plugin


class Raiser(Plugin):
    id = "raiser"
    version = "1.0.0"

    async def on_book_added(self, book) -> None:
        raise RuntimeError("intentional plugin failure")
""",
    )
    _write_plugin(
        tmp_path / "survivor",
        "survivor",
        """
from shelvr.plugins.base import Plugin


class Survivor(Plugin):
    id = "survivor"
    version = "1.0.0"
    saw_book = False

    async def on_book_added(self, book) -> None:
        type(self).saw_book = True
""",
    )

    loader = PluginLoader(tmp_path)
    registry = PluginRegistry()
    for entry in loader.discover():
        registry.register(entry)

    # Firing should not raise even though one plugin throws
    await registry.fire_event("on_book_added", book=object())

    survivor_loaded = registry.get("survivor")
    assert survivor_loaded is not None
    assert type(survivor_loaded.instance).saw_book is True


@pytest.mark.asyncio
async def test_registry_startup_calls_on_startup_for_every_plugin(tmp_path: Path) -> None:
    """startup() calls each plugin's on_startup."""
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    _write_plugin(
        tmp_path / "starter",
        "starter",
        """
from shelvr.plugins.base import Plugin


class Starter(Plugin):
    id = "starter"
    version = "1.0.0"
    started = False

    async def on_startup(self) -> None:
        type(self).started = True
""",
    )

    loader = PluginLoader(tmp_path)
    registry = PluginRegistry()
    for entry in loader.discover():
        registry.register(entry)

    await registry.startup()

    starter_loaded = registry.get("starter")
    assert starter_loaded is not None
    assert type(starter_loaded.instance).started is True


@pytest.mark.asyncio
async def test_registry_shutdown_calls_on_shutdown(tmp_path: Path) -> None:
    from shelvr.plugins.loader import PluginLoader
    from shelvr.plugins.registry import PluginRegistry

    _write_plugin(
        tmp_path / "stopper",
        "stopper",
        """
from shelvr.plugins.base import Plugin


class Stopper(Plugin):
    id = "stopper"
    version = "1.0.0"
    stopped = False

    async def on_shutdown(self) -> None:
        type(self).stopped = True
""",
    )

    loader = PluginLoader(tmp_path)
    registry = PluginRegistry()
    for entry in loader.discover():
        registry.register(entry)

    await registry.shutdown()
    stopper_loaded = registry.get("stopper")
    assert stopper_loaded is not None
    assert type(stopper_loaded.instance).stopped is True

"""Tests for the plugin base class and exception hierarchy."""

from __future__ import annotations

import pytest


def test_plugin_error_is_exception() -> None:
    from shelvr.plugins.exceptions import PluginError

    with pytest.raises(PluginError, match="boom"):
        raise PluginError("boom")


def test_manifest_error_is_plugin_error() -> None:
    from shelvr.plugins.exceptions import ManifestError, PluginError

    err = ManifestError("bad manifest")
    assert isinstance(err, PluginError)


def test_plugin_load_error_is_plugin_error() -> None:
    from shelvr.plugins.exceptions import PluginError, PluginLoadError

    err = PluginLoadError("module import failed")
    assert isinstance(err, PluginError)


def test_api_version_mismatch_is_plugin_error() -> None:
    from shelvr.plugins.exceptions import ApiVersionMismatchError, PluginError

    err = ApiVersionMismatchError("plugin wants api_version=99")
    assert isinstance(err, PluginError)


def test_plugin_context_construction() -> None:
    """PluginContext exposes plugin_id, logger, config."""
    import structlog

    from shelvr.plugins.context import PluginContext

    ctx = PluginContext(
        plugin_id="hello_world",
        logger=structlog.get_logger("plugin.hello_world"),
        config={"greeting": "hi"},
    )
    assert ctx.plugin_id == "hello_world"
    assert ctx.logger is not None
    assert ctx.config == {"greeting": "hi"}


def test_plugin_context_config_is_immutable() -> None:
    """PluginContext.config is a snapshot — modifying the input dict shouldn't bleed in."""
    import structlog

    from shelvr.plugins.context import PluginContext

    source = {"a": 1}
    ctx = PluginContext(
        plugin_id="x",
        logger=structlog.get_logger("plugin.x"),
        config=source,
    )
    source["a"] = 999
    assert ctx.config["a"] == 1


def test_plugin_subclass_minimum() -> None:
    """A Plugin subclass with just an id and version is valid."""
    import structlog

    from shelvr.plugins.base import Plugin
    from shelvr.plugins.context import PluginContext

    class MyPlugin(Plugin):
        id = "my_plugin"
        version = "1.0.0"

    ctx = PluginContext(
        plugin_id="my_plugin",
        logger=structlog.get_logger("plugin.my_plugin"),
        config={},
    )
    plugin = MyPlugin(ctx)
    assert plugin.id == "my_plugin"
    assert plugin.version == "1.0.0"
    assert plugin.ctx is ctx


@pytest.mark.asyncio
async def test_plugin_default_lifecycle_hooks_are_no_ops() -> None:
    """Default on_startup/on_shutdown/on_book_added do nothing and return None."""
    import structlog

    from shelvr.plugins.base import Plugin
    from shelvr.plugins.context import PluginContext

    class MyPlugin(Plugin):
        id = "noop"
        version = "1.0.0"

    plugin = MyPlugin(
        PluginContext(
            plugin_id="noop",
            logger=structlog.get_logger("plugin.noop"),
            config={},
        )
    )
    assert await plugin.on_startup() is None
    assert await plugin.on_shutdown() is None
    assert await plugin.on_book_added(book=object()) is None


@pytest.mark.asyncio
async def test_plugin_subclass_can_override_hook() -> None:
    """A plugin can override on_book_added and capture the book arg."""
    import structlog

    from shelvr.plugins.base import Plugin
    from shelvr.plugins.context import PluginContext

    seen_books: list[object] = []

    class CapturingPlugin(Plugin):
        id = "capturing"
        version = "1.0.0"

        async def on_book_added(self, book: object) -> None:
            seen_books.append(book)

    plugin = CapturingPlugin(
        PluginContext(
            plugin_id="capturing",
            logger=structlog.get_logger("plugin.capturing"),
            config={},
        )
    )
    sentinel = object()
    await plugin.on_book_added(book=sentinel)
    assert seen_books == [sentinel]

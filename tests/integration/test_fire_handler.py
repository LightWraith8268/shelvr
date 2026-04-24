"""Tests for handler-hook dispatch (priority-ordered, first non-None wins)."""

from __future__ import annotations

from pathlib import Path

import pytest
import structlog

from shelvr.plugins.base import Plugin
from shelvr.plugins.context import PluginContext
from shelvr.plugins.loader import LoadedPlugin
from shelvr.plugins.manifest import PluginManifest
from shelvr.plugins.registry import PluginRegistry


def _make_entry(plugin_id: str, instance_cls: type[Plugin], priority: int = 50) -> LoadedPlugin:
    ctx = PluginContext(
        plugin_id=plugin_id,
        logger=structlog.get_logger(f"plugin.{plugin_id}"),
        config={},
    )
    instance = instance_cls(ctx)
    manifest = PluginManifest(
        id=plugin_id, name=plugin_id, version="1.0.0", api_version="1", priority=priority
    )
    return LoadedPlugin(manifest=manifest, instance=instance)


@pytest.mark.asyncio
async def test_fire_handler_returns_first_non_none() -> None:
    """fire_handler returns the first non-None result, in priority order."""

    class LowPriority(Plugin):
        id = "low"
        version = "1.0.0"

        async def on_something(self, value: int) -> str | None:
            return f"low:{value}"

    class HighPriority(Plugin):
        id = "high"
        version = "1.0.0"

        async def on_something(self, value: int) -> str | None:
            return f"high:{value}"

    registry = PluginRegistry()
    registry.register(_make_entry("low", LowPriority, priority=10))
    registry.register(_make_entry("high", HighPriority, priority=99))

    result = await registry.fire_handler("on_something", value=7)
    assert result == "high:7"


@pytest.mark.asyncio
async def test_fire_handler_skips_plugins_returning_none() -> None:
    """fire_handler continues past plugins that return None."""

    class AlwaysNone(Plugin):
        id = "none"
        version = "1.0.0"

        async def on_pick(self, value: int) -> str | None:
            return None

    class AlwaysSomething(Plugin):
        id = "something"
        version = "1.0.0"

        async def on_pick(self, value: int) -> str | None:
            return f"got {value}"

    registry = PluginRegistry()
    registry.register(_make_entry("none", AlwaysNone, priority=99))
    registry.register(_make_entry("something", AlwaysSomething, priority=50))

    result = await registry.fire_handler("on_pick", value=42)
    assert result == "got 42"


@pytest.mark.asyncio
async def test_fire_handler_returns_none_when_no_plugins_match() -> None:
    class NullPlugin(Plugin):
        id = "null"
        version = "1.0.0"

    registry = PluginRegistry()
    registry.register(_make_entry("null", NullPlugin))

    # No plugin has on_never_fired
    result = await registry.fire_handler("on_never_fired", x=1)
    assert result is None


@pytest.mark.asyncio
async def test_fire_handler_isolates_plugin_failures() -> None:
    """A plugin raising doesn't stop the next plugin from getting a chance."""

    class Raiser(Plugin):
        id = "raiser"
        version = "1.0.0"

        async def on_do(self) -> str | None:
            raise RuntimeError("boom")

    class Survivor(Plugin):
        id = "survivor"
        version = "1.0.0"

        async def on_do(self) -> str | None:
            return "saved"

    registry = PluginRegistry()
    registry.register(_make_entry("raiser", Raiser, priority=99))
    registry.register(_make_entry("survivor", Survivor, priority=50))

    result = await registry.fire_handler("on_do")
    assert result == "saved"


def test_manifest_priority_defaults_to_50(tmp_path: Path) -> None:
    from shelvr.plugins.manifest import load_manifest

    path = tmp_path / "plugin.toml"
    path.write_text(
        """
[plugin]
id = "p"
name = "P"
version = "1.0.0"
api_version = "1"
""",
        encoding="utf-8",
    )
    manifest = load_manifest(path)
    assert manifest.priority == 50


def test_manifest_priority_can_be_set(tmp_path: Path) -> None:
    from shelvr.plugins.manifest import load_manifest

    path = tmp_path / "plugin.toml"
    path.write_text(
        """
[plugin]
id = "p"
name = "P"
version = "1.0.0"
api_version = "1"
priority = 99
""",
        encoding="utf-8",
    )
    manifest = load_manifest(path)
    assert manifest.priority == 99


def test_format_import_result_construction() -> None:
    from shelvr.formats.base import FormatImportResult, Metadata

    result = FormatImportResult(
        metadata=Metadata(title="Test"),
        cover_bytes=b"fake image",
    )
    assert result.metadata.title == "Test"
    assert result.cover_bytes == b"fake image"


def test_format_import_result_allows_no_cover() -> None:
    from shelvr.formats.base import FormatImportResult, Metadata

    result = FormatImportResult(metadata=Metadata(title="Test"), cover_bytes=None)
    assert result.cover_bytes is None

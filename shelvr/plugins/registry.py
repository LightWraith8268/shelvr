"""In-memory plugin registry and event dispatcher."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import structlog

from shelvr.plugins.loader import LoadedPlugin

_logger = structlog.get_logger(__name__)


class PluginRegistry:
    """Holds the set of loaded plugins and dispatches events to them.

    Errors raised by individual plugins during a fire_event/startup/shutdown
    call are logged with plugin_id context but do NOT propagate, so a single
    misbehaving plugin can't break the host or block other plugins.
    """

    def __init__(self) -> None:
        self._loaded: dict[str, LoadedPlugin] = {}

    def register(self, loaded: LoadedPlugin) -> None:
        """Add a loaded plugin. Replaces any existing entry with the same id."""
        self._loaded[loaded.manifest.id] = loaded

    def get(self, plugin_id: str) -> LoadedPlugin | None:
        return self._loaded.get(plugin_id)

    def all(self) -> Iterator[LoadedPlugin]:
        return iter(self._loaded.values())

    async def fire_event(self, event_name: str, /, **kwargs: Any) -> None:
        """Call ``event_name`` on every plugin that has it. Errors are logged, not raised."""
        for entry in self._loaded.values():
            await self._invoke(entry, event_name, **kwargs)

    async def startup(self) -> None:
        """Call on_startup on every plugin."""
        await self.fire_event("on_startup")

    async def shutdown(self) -> None:
        """Call on_shutdown on every plugin."""
        await self.fire_event("on_shutdown")

    @staticmethod
    async def _invoke(entry: LoadedPlugin, event_name: str, /, **kwargs: Any) -> None:
        """Invoke a single plugin's hook method, swallowing and logging errors."""
        method = getattr(entry.instance, event_name, None)
        if method is None or not callable(method):
            return
        try:
            result = method(**kwargs)
            if hasattr(result, "__await__"):
                await result
        except Exception as exc:
            _logger.warning(
                "plugin_event_failed",
                plugin_id=entry.manifest.id,
                event_name=event_name,
                error=str(exc),
            )

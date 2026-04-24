"""Plugin base class.

Subclass this in a plugin's `__init__.py`, set ``id`` and ``version`` class
attributes, optionally override the lifecycle/event hooks. The loader will
instantiate your subclass with a PluginContext.
"""

from __future__ import annotations

from typing import Any

from shelvr.plugins.context import PluginContext


class Plugin:
    """Base for all Shelvr plugins.

    Subclasses MUST set ``id: str`` and ``version: str`` as class attributes.
    Override ``async`` lifecycle and event hooks as needed; defaults are no-ops.
    """

    id: str = ""
    version: str = ""

    def __init__(self, ctx: PluginContext) -> None:
        self.ctx = ctx

    async def on_startup(self) -> None:
        """Called once after the plugin is loaded and before serving requests."""

    async def on_shutdown(self) -> None:
        """Called once when the server is shutting down or the plugin is disabled."""

    async def on_book_added(self, book: Any) -> None:
        """Fired after a new book is imported into the library."""

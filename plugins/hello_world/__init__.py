"""Reference plugin: logs a greeting whenever a book is added.

This plugin exists to prove the plugin loader, registry, and event dispatch
work end-to-end. It has no real functionality.
"""

from __future__ import annotations

from typing import Any

from shelvr.plugins.base import Plugin


class HelloWorldPlugin(Plugin):
    id = "hello_world"
    version = "1.0.0"

    async def on_startup(self) -> None:
        self.ctx.logger.info("hello_world_started", greeting=self.ctx.config.get("greeting"))

    async def on_book_added(self, book: Any) -> None:
        title = getattr(book, "title", "<unknown>")
        greeting = self.ctx.config.get("greeting", "hello")
        self.ctx.logger.info("hello_world_saw_book", greeting=greeting, title=title)

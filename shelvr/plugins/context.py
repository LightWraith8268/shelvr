"""PluginContext — what plugins receive at construction time."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from structlog.stdlib import BoundLogger


@dataclass(frozen=True)
class PluginContext:
    """Bundle of capabilities passed to a plugin at construction.

    v1 surface is intentionally narrow:
        - plugin_id: identifier from the manifest, useful for self-namespacing
        - logger:    structlog logger pre-bound with plugin_id
        - config:    snapshot of the plugin's config from plugin.toml [config]

    Day 5+ extends this with library/storage/http surfaces as the format-reader
    refactor needs them.
    """

    plugin_id: str
    logger: BoundLogger
    config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # frozen=True dataclass + dict field needs explicit copy to avoid aliasing
        object.__setattr__(self, "config", dict(self.config))

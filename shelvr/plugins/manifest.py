"""Plugin manifest schema and parser.

Manifest format (plugin.toml):

    [plugin]
    id = "my_plugin"
    name = "My Plugin"
    version = "1.0.0"
    api_version = "1"

    [hooks]            # optional
    on_book_added = true

    [config]           # optional - opaque to the host, plugin interprets
    greeting = "hello"
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shelvr.plugins.exceptions import ApiVersionMismatchError, ManifestError

SUPPORTED_API_VERSIONS: frozenset[str] = frozenset({"1"})

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


class PluginManifest(BaseModel):
    """Validated plugin manifest."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    version: str
    api_version: str
    priority: int = 50
    hooks: dict[str, bool] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        if not _ID_PATTERN.match(value):
            raise ValueError(
                "plugin id must be lowercase ASCII, start with a letter, and "
                "contain only letters, digits, underscores, or dashes"
            )
        return value


def load_manifest(path: Path) -> PluginManifest:
    """Load and validate a plugin.toml file.

    Raises:
        ManifestError: If the file is missing, unreadable, malformed, or fails
            schema validation.
        ApiVersionMismatchError: If the manifest declares an api_version this
            host doesn't support.
    """
    if not path.exists():
        raise ManifestError(f"plugin.toml not found at {path}")

    try:
        with path.open("rb") as f:
            raw = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"invalid TOML in {path}: {exc}") from exc

    plugin_section = raw.get("plugin")
    if not isinstance(plugin_section, dict):
        raise ManifestError(f"{path}: missing or invalid [plugin] section")

    fields: dict[str, Any] = {**plugin_section}
    if "hooks" in raw:
        fields["hooks"] = raw["hooks"]
    if "config" in raw:
        fields["config"] = raw["config"]

    try:
        manifest = PluginManifest(**fields)
    except ValidationError as exc:
        raise ManifestError(f"{path}: manifest validation failed: {exc}") from exc

    if manifest.api_version not in SUPPORTED_API_VERSIONS:
        raise ApiVersionMismatchError(
            f"{path}: plugin '{manifest.id}' declares api_version="
            f"{manifest.api_version!r} but this host supports "
            f"{sorted(SUPPORTED_API_VERSIONS)!r}"
        )

    return manifest

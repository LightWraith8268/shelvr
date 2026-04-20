"""Plugin system — discovery, loading, lifecycle, dispatch."""

from __future__ import annotations

from shelvr.plugins.base import Plugin
from shelvr.plugins.context import PluginContext
from shelvr.plugins.exceptions import (
    ApiVersionMismatchError,
    ManifestError,
    PluginError,
    PluginLoadError,
)
from shelvr.plugins.loader import LoadedPlugin, PluginLoader
from shelvr.plugins.manifest import PluginManifest, load_manifest
from shelvr.plugins.registry import PluginRegistry

__all__ = [
    "ApiVersionMismatchError",
    "LoadedPlugin",
    "ManifestError",
    "Plugin",
    "PluginContext",
    "PluginError",
    "PluginLoader",
    "PluginLoadError",
    "PluginManifest",
    "PluginRegistry",
    "load_manifest",
]

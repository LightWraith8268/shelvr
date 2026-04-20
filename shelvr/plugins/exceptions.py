"""Exception hierarchy for the plugin system."""

from __future__ import annotations


class PluginError(Exception):
    """Base class for all plugin-related errors."""


class ManifestError(PluginError):
    """Raised when a plugin.toml is missing, malformed, or fails validation."""


class PluginLoadError(PluginError):
    """Raised when a plugin's Python module cannot be imported or instantiated."""


class ApiVersionMismatchError(PluginError):
    """Raised when a plugin declares an api_version this host does not support."""

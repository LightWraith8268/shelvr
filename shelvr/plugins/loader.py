"""Plugin discovery and instantiation."""

from __future__ import annotations

import importlib.util
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import structlog

from shelvr.plugins.base import Plugin
from shelvr.plugins.context import PluginContext
from shelvr.plugins.exceptions import PluginError, PluginLoadError
from shelvr.plugins.manifest import PluginManifest, load_manifest

_logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class LoadedPlugin:
    """A successfully loaded plugin: its parsed manifest plus instance."""

    manifest: PluginManifest
    instance: Plugin


class PluginLoader:
    """Discovers and instantiates plugins from a directory.

    Each subdirectory of ``plugins_dir`` is examined; if it contains a
    ``plugin.toml``, we parse it, import the package, and find its Plugin
    subclass.

    Loading is best-effort — broken plugins are logged and skipped, never
    bubble out, so one bad plugin can't take the whole server down.
    """

    def __init__(self, plugins_dir: Path) -> None:
        self._plugins_dir = plugins_dir

    def discover(self) -> list[LoadedPlugin]:
        """Return all successfully-loaded plugins in the directory."""
        if not self._plugins_dir.exists() or not self._plugins_dir.is_dir():
            return []

        loaded: list[LoadedPlugin] = []
        for child in sorted(self._plugins_dir.iterdir()):
            if not child.is_dir():
                continue
            manifest_path = child / "plugin.toml"
            if not manifest_path.exists():
                continue
            try:
                loaded.append(self._load_one(child, manifest_path))
            except PluginError as exc:
                _logger.warning(
                    "plugin_load_failed",
                    plugin_dir=str(child),
                    error=str(exc),
                )
            except Exception as exc:  # defensive: don't let one bad plugin break the loader
                _logger.exception(
                    "plugin_load_unexpected_error",
                    plugin_dir=str(child),
                    error=str(exc),
                )
        return loaded

    def _load_one(self, plugin_dir: Path, manifest_path: Path) -> LoadedPlugin:
        manifest = load_manifest(manifest_path)
        plugin_class = self._import_plugin_class(plugin_dir, manifest.id)
        ctx = PluginContext(
            plugin_id=manifest.id,
            logger=structlog.get_logger("plugin").bind(plugin_id=manifest.id),
            config=manifest.config,
        )
        instance = plugin_class(ctx)
        return LoadedPlugin(manifest=manifest, instance=instance)

    def _import_plugin_class(self, plugin_dir: Path, plugin_id: str) -> type[Plugin]:
        """Import the plugin's __init__.py and return its Plugin subclass."""
        init_path = plugin_dir / "__init__.py"
        if not init_path.exists():
            raise PluginLoadError(f"{plugin_dir}: missing __init__.py")

        # Plugin IDs may contain dots (e.g. "builtin.epub") to namespace them,
        # but a dot in a Python module name is a submodule separator and breaks
        # importlib/sys.modules. Sanitize dots to underscores for the internal
        # module key; the plugin's declared id remains unchanged.
        safe_id = plugin_id.replace(".", "_")
        module_name = f"shelvr_plugin_{safe_id}"
        spec = importlib.util.spec_from_file_location(
            module_name, init_path, submodule_search_locations=[str(plugin_dir)]
        )
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"{plugin_dir}: cannot create import spec")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            sys.modules.pop(module_name, None)
            raise PluginLoadError(f"{plugin_dir}: import failed: {exc}") from exc

        plugin_class = self._find_plugin_subclass(module)
        if plugin_class is None:
            raise PluginLoadError(f"{plugin_dir}: no Plugin subclass exported from __init__.py")
        return plugin_class

    @staticmethod
    def _find_plugin_subclass(module: ModuleType) -> type[Plugin] | None:
        for _, value in inspect.getmembers(module):
            if inspect.isclass(value) and issubclass(value, Plugin) and value is not Plugin:
                return value
        return None

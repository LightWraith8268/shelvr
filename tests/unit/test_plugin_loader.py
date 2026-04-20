"""Tests for the plugin loader."""

from __future__ import annotations

from pathlib import Path


def _write_plugin(plugin_dir: Path, plugin_id: str) -> None:
    """Write a minimal valid plugin into ``plugin_dir``."""
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.toml").write_text(
        f"""
[plugin]
id = "{plugin_id}"
name = "Plugin {plugin_id}"
version = "1.0.0"
api_version = "1"
""",
        encoding="utf-8",
    )
    (plugin_dir / "__init__.py").write_text(
        f"""
from shelvr.plugins.base import Plugin


class MyPlugin(Plugin):
    id = "{plugin_id}"
    version = "1.0.0"
""",
        encoding="utf-8",
    )


def test_loader_discovers_one_plugin(tmp_path: Path) -> None:
    from shelvr.plugins.loader import PluginLoader

    _write_plugin(tmp_path / "alpha", "alpha")

    loader = PluginLoader(tmp_path)
    loaded = loader.discover()

    assert len(loaded) == 1
    assert loaded[0].manifest.id == "alpha"
    assert loaded[0].instance.id == "alpha"


def test_loader_discovers_multiple_plugins(tmp_path: Path) -> None:
    from shelvr.plugins.loader import PluginLoader

    _write_plugin(tmp_path / "alpha", "alpha")
    _write_plugin(tmp_path / "bravo", "bravo")

    loader = PluginLoader(tmp_path)
    loaded = loader.discover()

    assert {entry.manifest.id for entry in loaded} == {"alpha", "bravo"}


def test_loader_skips_dirs_without_manifest(tmp_path: Path) -> None:
    from shelvr.plugins.loader import PluginLoader

    _write_plugin(tmp_path / "real", "real")
    (tmp_path / "not_a_plugin").mkdir()
    (tmp_path / "not_a_plugin" / "README.md").write_text("just a folder", encoding="utf-8")

    loader = PluginLoader(tmp_path)
    loaded = loader.discover()
    assert {entry.manifest.id for entry in loaded} == {"real"}


def test_loader_skips_plugin_with_invalid_manifest(tmp_path: Path) -> None:
    """A plugin with an invalid manifest is logged and skipped (not raised)."""
    from shelvr.plugins.loader import PluginLoader

    good = tmp_path / "good"
    _write_plugin(good, "good")

    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "plugin.toml").write_text("not valid toml [", encoding="utf-8")
    (bad / "__init__.py").write_text("", encoding="utf-8")

    loader = PluginLoader(tmp_path)
    loaded = loader.discover()
    assert {entry.manifest.id for entry in loaded} == {"good"}


def test_loader_skips_plugin_without_plugin_subclass(tmp_path: Path) -> None:
    """A plugin whose __init__.py defines no Plugin subclass is skipped."""
    from shelvr.plugins.loader import PluginLoader

    good = tmp_path / "good"
    _write_plugin(good, "good")

    bad = tmp_path / "no_class"
    bad.mkdir()
    (bad / "plugin.toml").write_text(
        """
[plugin]
id = "no_class"
name = "No Class"
version = "1.0.0"
api_version = "1"
""",
        encoding="utf-8",
    )
    (bad / "__init__.py").write_text("# no Plugin subclass here\n", encoding="utf-8")

    loader = PluginLoader(tmp_path)
    loaded = loader.discover()
    assert {entry.manifest.id for entry in loaded} == {"good"}


def test_loader_returns_empty_when_dir_missing(tmp_path: Path) -> None:
    """Pointing at a non-existent dir is not an error — just no plugins."""
    from shelvr.plugins.loader import PluginLoader

    loader = PluginLoader(tmp_path / "does_not_exist")
    loaded = loader.discover()
    assert loaded == []

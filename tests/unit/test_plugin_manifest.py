"""Tests for plugin manifest parsing."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_manifest_minimal(tmp_path: Path) -> None:
    """A manifest with just [plugin] required fields parses."""
    from shelvr.plugins.manifest import load_manifest

    manifest_path = tmp_path / "plugin.toml"
    manifest_path.write_text(
        """
[plugin]
id = "my_plugin"
name = "My Plugin"
version = "1.0.0"
api_version = "1"
""",
        encoding="utf-8",
    )

    manifest = load_manifest(manifest_path)
    assert manifest.id == "my_plugin"
    assert manifest.name == "My Plugin"
    assert manifest.version == "1.0.0"
    assert manifest.api_version == "1"
    assert manifest.hooks == {}
    assert manifest.config == {}


def test_manifest_with_hooks(tmp_path: Path) -> None:
    """[hooks] section is parsed into a dict."""
    from shelvr.plugins.manifest import load_manifest

    manifest_path = tmp_path / "plugin.toml"
    manifest_path.write_text(
        """
[plugin]
id = "h"
name = "Hooks"
version = "1.0.0"
api_version = "1"

[hooks]
on_startup = true
on_book_added = true
on_shutdown = false
""",
        encoding="utf-8",
    )

    manifest = load_manifest(manifest_path)
    assert manifest.hooks["on_startup"] is True
    assert manifest.hooks["on_book_added"] is True
    assert manifest.hooks["on_shutdown"] is False


def test_manifest_with_config(tmp_path: Path) -> None:
    """[config] section is captured as opaque dict for the plugin to interpret."""
    from shelvr.plugins.manifest import load_manifest

    manifest_path = tmp_path / "plugin.toml"
    manifest_path.write_text(
        """
[plugin]
id = "c"
name = "Cfg"
version = "1.0.0"
api_version = "1"

[config]
greeting = "hello"
verbosity = 3
enabled_features = ["a", "b"]
""",
        encoding="utf-8",
    )

    manifest = load_manifest(manifest_path)
    assert manifest.config["greeting"] == "hello"
    assert manifest.config["verbosity"] == 3
    assert manifest.config["enabled_features"] == ["a", "b"]


def test_manifest_missing_file_raises(tmp_path: Path) -> None:
    from shelvr.plugins.exceptions import ManifestError
    from shelvr.plugins.manifest import load_manifest

    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "nope.toml")


def test_manifest_invalid_toml_raises(tmp_path: Path) -> None:
    from shelvr.plugins.exceptions import ManifestError
    from shelvr.plugins.manifest import load_manifest

    bad = tmp_path / "plugin.toml"
    bad.write_text("[plugin\nthis isn't TOML", encoding="utf-8")

    with pytest.raises(ManifestError):
        load_manifest(bad)


def test_manifest_missing_required_field_raises(tmp_path: Path) -> None:
    """Missing 'id' (required) raises ManifestError."""
    from shelvr.plugins.exceptions import ManifestError
    from shelvr.plugins.manifest import load_manifest

    bad = tmp_path / "plugin.toml"
    bad.write_text(
        """
[plugin]
name = "No ID"
version = "1.0.0"
api_version = "1"
""",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError):
        load_manifest(bad)


def test_manifest_invalid_id_raises(tmp_path: Path) -> None:
    """id must match a sane identifier pattern (lowercase, underscore, dash)."""
    from shelvr.plugins.exceptions import ManifestError
    from shelvr.plugins.manifest import load_manifest

    bad = tmp_path / "plugin.toml"
    bad.write_text(
        """
[plugin]
id = "Invalid Spaces!"
name = "Bad ID"
version = "1.0.0"
api_version = "1"
""",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError):
        load_manifest(bad)


def test_manifest_unsupported_api_version_raises(tmp_path: Path) -> None:
    """Loading a manifest declaring api_version != supported raises."""
    from shelvr.plugins.exceptions import ApiVersionMismatchError
    from shelvr.plugins.manifest import load_manifest

    fut = tmp_path / "plugin.toml"
    fut.write_text(
        """
[plugin]
id = "future"
name = "Future"
version = "1.0.0"
api_version = "99"
""",
        encoding="utf-8",
    )

    with pytest.raises(ApiVersionMismatchError):
        load_manifest(fut)


def test_manifest_accepts_dotted_namespace_id(tmp_path: Path) -> None:
    """Plugin IDs can use dots as namespace separators (e.g. 'builtin.epub')."""
    from shelvr.plugins.manifest import load_manifest

    path = tmp_path / "plugin.toml"
    path.write_text(
        """
[plugin]
id = "builtin.epub"
name = "Namespaced"
version = "1.0.0"
api_version = "1"
""",
        encoding="utf-8",
    )

    manifest = load_manifest(path)
    assert manifest.id == "builtin.epub"


def test_manifest_rejects_id_starting_with_dot(tmp_path: Path) -> None:
    """IDs cannot start with a dot."""
    from shelvr.plugins.exceptions import ManifestError
    from shelvr.plugins.manifest import load_manifest

    path = tmp_path / "plugin.toml"
    path.write_text(
        """
[plugin]
id = ".builtin"
name = "Bad"
version = "1.0.0"
api_version = "1"
""",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError):
        load_manifest(path)


def test_manifest_rejects_id_with_trailing_dot(tmp_path: Path) -> None:
    """IDs cannot end with a dot."""
    from shelvr.plugins.exceptions import ManifestError
    from shelvr.plugins.manifest import load_manifest

    path = tmp_path / "plugin.toml"
    path.write_text(
        """
[plugin]
id = "builtin."
name = "Bad"
version = "1.0.0"
api_version = "1"
""",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError):
        load_manifest(path)

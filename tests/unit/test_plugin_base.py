"""Tests for the plugin base class and exception hierarchy."""

from __future__ import annotations

import pytest


def test_plugin_error_is_exception() -> None:
    from shelvr.plugins.exceptions import PluginError

    with pytest.raises(PluginError, match="boom"):
        raise PluginError("boom")


def test_manifest_error_is_plugin_error() -> None:
    from shelvr.plugins.exceptions import ManifestError, PluginError

    err = ManifestError("bad manifest")
    assert isinstance(err, PluginError)


def test_plugin_load_error_is_plugin_error() -> None:
    from shelvr.plugins.exceptions import PluginError, PluginLoadError

    err = PluginLoadError("module import failed")
    assert isinstance(err, PluginError)


def test_api_version_mismatch_is_plugin_error() -> None:
    from shelvr.plugins.exceptions import ApiVersionMismatchError, PluginError

    err = ApiVersionMismatchError("plugin wants api_version=99")
    assert isinstance(err, PluginError)

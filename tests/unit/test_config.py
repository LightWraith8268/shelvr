"""Tests for the Shelvr settings loader."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from shelvr.config import Settings, load_settings


def test_defaults_applied(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Default values are used when no config file and no env vars are set."""
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.delenv("SHELVR_HOST", raising=False)
    monkeypatch.delenv("SHELVR_PORT", raising=False)

    settings = load_settings(config_file=None)

    assert settings.host == "127.0.0.1"
    assert settings.port == 7654
    assert settings.library_path == tmp_path
    assert settings.database_url == "sqlite+aiosqlite:///shelvr.db"
    assert settings.log_level == "INFO"
    assert settings.jwt_access_ttl_minutes == 15
    assert settings.jwt_refresh_ttl_days == 30


def test_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """SHELVR_* env vars override defaults."""
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_HOST", "0.0.0.0")
    monkeypatch.setenv("SHELVR_PORT", "9999")
    monkeypatch.setenv("SHELVR_LOG_LEVEL", "DEBUG")

    settings = load_settings(config_file=None)

    assert settings.host == "0.0.0.0"
    assert settings.port == 9999
    assert settings.log_level == "DEBUG"


def test_toml_file_overrides_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Values in shelvr.toml override defaults."""
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test-secret")
    library = tmp_path / "lib"
    library.mkdir()
    config_file = tmp_path / "shelvr.toml"
    config_file.write_text(
        f"""
host = "10.0.0.1"
port = 8888
library_path = "{library.as_posix()}"
log_level = "WARNING"
""",
        encoding="utf-8",
    )

    settings = load_settings(config_file=config_file)

    assert settings.host == "10.0.0.1"
    assert settings.port == 8888
    assert settings.library_path == library
    assert settings.log_level == "WARNING"


def test_env_beats_toml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Env vars win over shelvr.toml values."""
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SHELVR_HOST", "192.168.1.1")
    library = tmp_path / "lib"
    library.mkdir()
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(library))
    config_file = tmp_path / "shelvr.toml"
    config_file.write_text('host = "10.0.0.1"\nport = 8888\n', encoding="utf-8")

    settings = load_settings(config_file=config_file)

    assert settings.host == "192.168.1.1"  # env wins over TOML
    assert settings.port == 8888  # TOML-only field still applied


def test_missing_jwt_secret_fails_loudly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """jwt_secret is required — loading settings without it must raise."""
    monkeypatch.delenv("SHELVR_JWT_SECRET", raising=False)
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))

    with pytest.raises(ValidationError):
        load_settings(config_file=None)


def test_settings_type_is_frozen() -> None:
    """Settings should not be mutable after load (defensive)."""
    settings = Settings(
        library_path=Path("/tmp/lib"),
        jwt_secret="x",
    )
    with pytest.raises(ValidationError):
        settings.host = "mutated"  # type: ignore[misc]

"""Shelvr settings loader.

Precedence (lowest to highest):
    defaults -> shelvr.toml -> SHELVR_* environment variables
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class _TomlSource(PydanticBaseSettingsSource):
    """A pydantic-settings source that supplies values from an already-loaded TOML dict.

    Placed below env in the precedence chain so env vars override TOML values.
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        toml_values: dict[str, Any],
    ) -> None:
        super().__init__(settings_cls)
        self._toml_values = toml_values

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        if field_name in self._toml_values:
            return self._toml_values[field_name], field_name, False
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        return dict(self._toml_values)


class Settings(BaseSettings):
    """Shelvr runtime configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SHELVR_",
        env_file=None,
        frozen=True,
        extra="ignore",
    )

    host: str = Field(
        default="127.0.0.1",
        description=("Bind address. Localhost-only by default; LAN exposure is explicit opt-in."),
    )
    port: int = Field(default=7654, ge=1, le=65535)
    library_path: Path = Field(..., description="Root directory of the ebook library.")
    database_url: str = Field(default="sqlite+aiosqlite:///shelvr.db")
    plugin_dir: Path = Field(default=Path("plugins"))
    log_level: str = Field(default="INFO")
    jwt_secret: str = Field(..., min_length=1, description="Required; fail loudly if missing.")
    jwt_access_ttl_minutes: int = Field(default=15, ge=1)
    jwt_refresh_ttl_days: int = Field(default=30, ge=1)


def _read_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file into a dict. Returns empty dict if the file does not exist."""
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def load_settings(config_file: Path | None = Path("shelvr.toml")) -> Settings:
    """Load Shelvr settings with defaults -> TOML -> env precedence.

    Args:
        config_file: Path to shelvr.toml. Pass None to skip file loading.

    Returns:
        A frozen Settings instance.

    Raises:
        pydantic.ValidationError: If required fields are missing or invalid.
    """
    toml_values = _read_toml(config_file) if config_file is not None else {}

    # Build a one-off Settings subclass whose source chain puts TOML *below* env,
    # so SHELVR_* environment variables override anything in shelvr.toml.
    # Nested subclass lets us close over toml_values without a module-level global.
    class _SettingsWithToml(Settings):
        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            return (
                init_settings,
                env_settings,
                dotenv_settings,
                _TomlSource(settings_cls, toml_values),
                file_secret_settings,
            )

    return _SettingsWithToml()

"""Pydantic schemas for the plugin admin API."""

from __future__ import annotations

from pydantic import BaseModel


class PluginRead(BaseModel):
    """Public-safe shape for a loaded plugin."""

    id: str
    name: str
    version: str
    api_version: str
    priority: int
    enabled: bool
    hooks: list[str]


class PluginUpdate(BaseModel):
    """Body for PATCH /api/v1/plugins/{id}."""

    enabled: bool

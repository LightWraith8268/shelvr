"""Plugin admin endpoints — list and toggle enabled state."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.api.deps import get_session
from shelvr.auth.deps import require_admin
from shelvr.db.models import User
from shelvr.plugins import PluginRegistry
from shelvr.repositories.plugin_state import PluginStateRepository
from shelvr.schemas.plugin import PluginUpdate

router = APIRouter(prefix="/plugins", tags=["plugins"])


def _registry(request: Request) -> PluginRegistry:
    return request.app.state.plugins  # type: ignore[no-any-return]


def _serialize(registry: PluginRegistry, plugin_id: str) -> dict[str, Any] | None:
    entry = registry.get(plugin_id)
    if entry is None:
        return None
    return {
        "id": entry.manifest.id,
        "name": entry.manifest.name,
        "version": entry.manifest.version,
        "api_version": entry.manifest.api_version,
        "priority": entry.manifest.priority,
        "enabled": registry.is_enabled(entry.manifest.id),
        "hooks": sorted(name for name, on in entry.manifest.hooks.items() if on),
    }


@router.get("")
async def list_plugins(
    request: Request,
    _admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """Return every loaded plugin with its current enabled flag."""
    registry = _registry(request)
    items = [_serialize(registry, entry.manifest.id) for entry in registry.all()]
    return {"items": [item for item in items if item is not None]}


@router.patch("/{plugin_id}")
async def update_plugin(
    plugin_id: str,
    update: PluginUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """Toggle a plugin's enabled flag and persist the choice."""
    registry = _registry(request)
    if registry.get(plugin_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="plugin not found")
    registry.set_enabled(plugin_id, update.enabled)
    await PluginStateRepository(session).set_enabled(plugin_id, update.enabled)
    await session.commit()
    serialized = _serialize(registry, plugin_id)
    assert serialized is not None  # narrow for type-checker
    return serialized

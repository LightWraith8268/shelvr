"""Plugin admin endpoints — list, toggle enabled state, install, uninstall."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.api.deps import get_session, get_settings
from shelvr.auth.deps import require_admin
from shelvr.config import Settings
from shelvr.db.models import User
from shelvr.plugins import PluginRegistry
from shelvr.repositories.plugin_state import PluginStateRepository
from shelvr.schemas.plugin import PluginUpdate
from shelvr.services.plugin_upload import (
    PluginUploadError,
    install_plugin_zip,
    remove_installed_plugin,
)

BUILTIN_PLUGINS_DIR = (Path(__file__).resolve().parents[2] / "plugins" / "builtin").resolve()

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


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_plugin(
    file: UploadFile,
    overwrite: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
    _admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """Install a plugin from an uploaded zip archive. Admin only.

    The plugin runs in-process — installation grants full code-execution
    privilege. Validation only blocks malformed archives, traversal entries,
    and oversize payloads. The new plugin loads on next server restart.
    """
    payload = await file.read()
    try:
        installed = install_plugin_zip(
            zip_bytes=payload, plugins_dir=settings.plugin_dir, overwrite=overwrite
        )
    except PluginUploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "id": installed.manifest.id,
        "name": installed.manifest.name,
        "version": installed.manifest.version,
        "install_path": str(installed.install_path),
        "restart_required": True,
    }


@router.delete("/{plugin_id}/install", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_plugin(
    plugin_id: str,
    settings: Settings = Depends(get_settings),
    _admin: User = Depends(require_admin),
) -> None:
    """Remove a previously-installed user plugin from disk. Built-ins are protected.

    Plugin code already loaded into the running process stays loaded until
    restart; this only deletes its source files so it won't reappear.
    """
    candidate_dir = (settings.plugin_dir / plugin_id).resolve()
    builtin_candidate = (BUILTIN_PLUGINS_DIR / plugin_id).resolve()
    if candidate_dir == builtin_candidate or builtin_candidate.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="built-in plugins cannot be uninstalled",
        )
    removed = remove_installed_plugin(plugin_id=plugin_id, plugins_dir=settings.plugin_dir)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="plugin not installed")
    return None


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

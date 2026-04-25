"""Repository for plugin enable/disable state.

Persisted in the existing ``plugin_data`` KV table under a sentinel
``plugin_id="_shelvr"`` namespace so we don't have to invent a new table or
collide with plugins' own per-plugin keys.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.db.models import PluginData

_HOST_NAMESPACE = "_shelvr"


def _enabled_key(plugin_id: str) -> str:
    return f"plugin_enabled:{plugin_id}"


class PluginStateRepository:
    """Read/write the enabled flag for each loaded plugin."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load_all(self) -> dict[str, bool]:
        """Return ``{plugin_id: enabled}`` for every plugin with a stored state."""
        prefix = "plugin_enabled:"
        statement = select(PluginData).where(PluginData.plugin_id == _HOST_NAMESPACE)
        rows = (await self._session.execute(statement)).scalars().all()
        out: dict[str, bool] = {}
        for row in rows:
            if not row.key.startswith(prefix):
                continue
            try:
                value = json.loads(row.value_json)
            except json.JSONDecodeError:
                continue
            if isinstance(value, bool):
                out[row.key[len(prefix) :]] = value
        return out

    async def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        key = _enabled_key(plugin_id)
        existing = (
            await self._session.execute(
                select(PluginData).where(
                    PluginData.plugin_id == _HOST_NAMESPACE, PluginData.key == key
                )
            )
        ).scalar_one_or_none()
        encoded = json.dumps(enabled)
        if existing is None:
            self._session.add(PluginData(plugin_id=_HOST_NAMESPACE, key=key, value_json=encoded))
        else:
            existing.value_json = encoded
        await self._session.flush()

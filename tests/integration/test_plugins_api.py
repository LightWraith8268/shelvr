"""Integration tests for /api/v1/plugins admin endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


async def _setup_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from shelvr.auth.deps import get_current_user, require_admin
    from shelvr.db.base import Base
    from shelvr.db.models import User
    from shelvr.main import create_app

    test_app = create_app()
    async with test_app.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    fake_admin = User(id=1, username="admin", password_hash="x", role="admin", is_active=True)
    test_app.dependency_overrides[get_current_user] = lambda: fake_admin
    test_app.dependency_overrides[require_admin] = lambda: fake_admin
    return test_app


@pytest.mark.asyncio
async def test_list_plugins_returns_loaded_built_ins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/plugins")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    ids = {item["id"] for item in items}
    # Built-in EPUB / PDF / MOBI plugins ship in-tree.
    assert "builtin.epub" in ids
    for item in items:
        assert item["enabled"] is True
        assert "hooks" in item


@pytest.mark.asyncio
async def test_patch_plugin_disables_then_enables(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        disable = await client.patch("/api/v1/plugins/builtin.epub", json={"enabled": False})
        assert disable.status_code == 200
        assert disable.json()["enabled"] is False

        # Registry reflects the change.
        assert test_app.state.plugins.is_enabled("builtin.epub") is False

        listed = await client.get("/api/v1/plugins")
        epub = next(item for item in listed.json()["items"] if item["id"] == "builtin.epub")
        assert epub["enabled"] is False

        enable = await client.patch("/api/v1/plugins/builtin.epub", json={"enabled": True})
        assert enable.status_code == 200
        assert enable.json()["enabled"] is True


@pytest.mark.asyncio
async def test_patch_unknown_plugin_returns_404(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch("/api/v1/plugins/no.such.plugin", json={"enabled": True})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_disabled_plugin_state_persists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Toggling enabled writes through to plugin_data so a fresh app picks it up."""
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.patch("/api/v1/plugins/builtin.epub", json={"enabled": False})

    from shelvr.repositories.plugin_state import PluginStateRepository

    async with test_app.state.session_factory() as session:
        state = await PluginStateRepository(session).load_all()
    assert state.get("builtin.epub") is False


@pytest.mark.asyncio
async def test_list_plugins_requires_admin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Override get_current_user to a reader; require_admin must 403."""
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from fastapi import HTTPException
    from fastapi import status as http_status

    from shelvr.auth.deps import get_current_user, require_admin
    from shelvr.db.base import Base
    from shelvr.db.models import User
    from shelvr.main import create_app

    test_app = create_app()
    async with test_app.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    reader = User(id=2, username="reader", password_hash="x", role="reader", is_active=True)

    def _admin_required() -> User:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN, detail="admin role required"
        )

    test_app.dependency_overrides[get_current_user] = lambda: reader
    test_app.dependency_overrides[require_admin] = _admin_required

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        listed = await client.get("/api/v1/plugins")
        assert listed.status_code == 403
        patched = await client.patch("/api/v1/plugins/builtin.epub", json={"enabled": False})
        assert patched.status_code == 403

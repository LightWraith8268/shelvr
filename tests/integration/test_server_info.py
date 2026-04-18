"""Integration test for GET /api/v1/server/info."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_server_info_returns_expected_shape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    """GET /api/v1/server/info returns version, protocol_version, and features."""
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from shelvr.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/server/info")

    assert response.status_code == 200
    body = response.json()
    assert "version" in body
    assert "protocol_version" in body
    assert "features" in body
    assert isinstance(body["features"], list)
    assert "opds" in body["features"]
    assert "plugins" in body["features"]
    assert "jwt_auth" in body["features"]
    assert body["protocol_version"] == 1


@pytest.mark.asyncio
async def test_server_info_sets_request_id_header(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    """Responses include an X-Request-ID header for traceability."""
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from shelvr.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/server/info")

    assert response.status_code == 200
    assert "x-request-id" in {k.lower() for k in response.headers}

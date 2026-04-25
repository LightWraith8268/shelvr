"""Integration tests covering get_current_user / require_admin enforcement."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from shelvr.auth.passwords import hash_password
from shelvr.auth.tokens import issue_access_token
from shelvr.db.models import User
from shelvr.main import create_app


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FastAPI:
    monkeypatch.setenv("SHELVR_JWT_SECRET", "gating-secret")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    return create_app()


async def _seed(app: FastAPI, *, role: str = "reader", is_active: bool = True) -> int:
    from shelvr.db.base import Base

    engine = app.state.engine
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with app.state.session_factory() as session:
        user = User(
            username=f"u-{role}",
            password_hash=hash_password("pw"),
            role=role,
            is_active=is_active,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


def _bearer_for(user_id: int, role: str) -> dict[str, str]:
    token = issue_access_token(user_id=user_id, role=role, secret="gating-secret", ttl_minutes=15)
    return {"Authorization": f"Bearer {token}"}


async def _client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_books_list_requires_authentication(app: FastAPI) -> None:
    await _seed(app)
    async for client in _client(app):
        response = await client.get("/api/v1/books")
        assert response.status_code == 401
        assert response.headers.get("www-authenticate", "").lower().startswith("bearer")


@pytest.mark.asyncio
async def test_books_list_rejects_garbage_token(app: FastAPI) -> None:
    await _seed(app)
    async for client in _client(app):
        response = await client.get("/api/v1/books", headers={"Authorization": "Bearer not-a-jwt"})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_books_list_accepts_valid_token(app: FastAPI) -> None:
    user_id = await _seed(app)
    async for client in _client(app):
        response = await client.get("/api/v1/books", headers=_bearer_for(user_id, "reader"))
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_books_list_rejects_inactive_user(app: FastAPI) -> None:
    user_id = await _seed(app, is_active=False)
    async for client in _client(app):
        response = await client.get("/api/v1/books", headers=_bearer_for(user_id, "reader"))
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_requires_admin_role(app: FastAPI) -> None:
    user_id = await _seed(app, role="reader")
    async for client in _client(app):
        response = await client.post(
            "/api/v1/books",
            headers=_bearer_for(user_id, "reader"),
            files={"file": ("book.epub", b"not a real epub", "application/epub+zip")},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_server_info_is_public(app: FastAPI) -> None:
    """/server/info must remain reachable without a token for client discovery."""
    await _seed(app)
    async for client in _client(app):
        response = await client.get("/api/v1/server/info")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_me_returns_current_user(app: FastAPI) -> None:
    user_id = await _seed(app, role="admin")
    async for client in _client(app):
        response = await client.get("/api/v1/auth/me", headers=_bearer_for(user_id, "admin"))
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == user_id
        assert body["role"] == "admin"
        assert "password_hash" not in body


@pytest.mark.asyncio
async def test_me_requires_authentication(app: FastAPI) -> None:
    await _seed(app)
    async for client in _client(app):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_refresh_token(app: FastAPI) -> None:
    """A refresh token must not be usable as an access token."""
    from shelvr.auth.tokens import issue_refresh_token

    user_id = await _seed(app)
    refresh = issue_refresh_token(user_id=user_id, secret="gating-secret", ttl_days=30)
    async for client in _client(app):
        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh.token}"}
        )
        assert response.status_code == 401

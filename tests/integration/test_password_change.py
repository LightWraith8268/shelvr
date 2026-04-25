"""Integration tests for POST /api/v1/auth/me/password."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from shelvr.auth.passwords import hash_password
from shelvr.db.models import User
from shelvr.main import create_app


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FastAPI:
    monkeypatch.setenv("SHELVR_JWT_SECRET", "pwd-test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    return create_app()


async def _seed_user(
    app: FastAPI, *, username: str = "alice", password: str = "hunter2-old"
) -> int:
    from shelvr.db.base import Base

    async with app.state.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with app.state.session_factory() as session:
        user = User(username=username, password_hash=hash_password(password), role="reader")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def _client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_change_password_happy_path(app: FastAPI) -> None:
    await _seed_user(app)
    async for client in _client(app):
        login = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "hunter2-old"}
        )
        access = login.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/me/password",
            headers={"Authorization": f"Bearer {access}"},
            json={"current_password": "hunter2-old", "new_password": "hunter2-new"},
        )
        assert response.status_code == 204

        # Old password no longer works.
        bad = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "hunter2-old"}
        )
        assert bad.status_code == 401

        # New password works.
        good = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "hunter2-new"}
        )
        assert good.status_code == 200


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_current(app: FastAPI) -> None:
    await _seed_user(app)
    async for client in _client(app):
        login = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "hunter2-old"}
        )
        access = login.json()["access_token"]
        response = await client.post(
            "/api/v1/auth/me/password",
            headers={"Authorization": f"Bearer {access}"},
            json={"current_password": "WRONG", "new_password": "hunter2-new"},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_change_password_rejects_short_new(app: FastAPI) -> None:
    await _seed_user(app)
    async for client in _client(app):
        login = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "hunter2-old"}
        )
        access = login.json()["access_token"]
        response = await client.post(
            "/api/v1/auth/me/password",
            headers={"Authorization": f"Bearer {access}"},
            json={"current_password": "hunter2-old", "new_password": "short"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password_revokes_existing_refresh_tokens(app: FastAPI) -> None:
    await _seed_user(app)
    async for client in _client(app):
        login = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "hunter2-old"}
        )
        old_access = login.json()["access_token"]
        old_refresh = login.json()["refresh_token"]

        change = await client.post(
            "/api/v1/auth/me/password",
            headers={"Authorization": f"Bearer {old_access}"},
            json={"current_password": "hunter2-old", "new_password": "hunter2-new"},
        )
        assert change.status_code == 204

        # Refresh token from before the rotation must be revoked.
        replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert replay.status_code == 401


@pytest.mark.asyncio
async def test_change_password_requires_authentication(app: FastAPI) -> None:
    await _seed_user(app)
    async for client in _client(app):
        response = await client.post(
            "/api/v1/auth/me/password",
            json={"current_password": "x", "new_password": "yyyyyyyy"},
        )
        assert response.status_code == 401

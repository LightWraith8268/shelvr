"""Integration tests for POST /api/v1/auth/me/username."""

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
    monkeypatch.setenv("SHELVR_JWT_SECRET", "username-test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    return create_app()


async def _seed(app: FastAPI, *, users: list[tuple[str, str]]) -> None:
    from shelvr.db.base import Base

    async with app.state.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with app.state.session_factory() as session:
        for username, password in users:
            session.add(
                User(username=username, password_hash=hash_password(password), role="reader")
            )
        await session.commit()


async def _client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_change_username_happy_path(app: FastAPI) -> None:
    await _seed(app, users=[("alice", "pw-alice")])
    async for client in _client(app):
        login = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "pw-alice"}
        )
        access = login.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/me/username",
            headers={"Authorization": f"Bearer {access}"},
            json={"current_password": "pw-alice", "new_username": "alice2"},
        )
        assert response.status_code == 200
        assert response.json()["username"] == "alice2"

        # Existing access token still works (sub binds to user_id, not username).
        me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200
        assert me.json()["username"] == "alice2"

        # Old username can't log in any more.
        old = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "pw-alice"}
        )
        assert old.status_code == 401

        # New username can.
        new = await client.post(
            "/api/v1/auth/login", json={"username": "alice2", "password": "pw-alice"}
        )
        assert new.status_code == 200


@pytest.mark.asyncio
async def test_change_username_rejects_wrong_password(app: FastAPI) -> None:
    await _seed(app, users=[("alice", "pw-alice")])
    async for client in _client(app):
        login = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "pw-alice"}
        )
        access = login.json()["access_token"]
        response = await client.post(
            "/api/v1/auth/me/username",
            headers={"Authorization": f"Bearer {access}"},
            json={"current_password": "WRONG", "new_username": "alice2"},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_change_username_conflict(app: FastAPI) -> None:
    await _seed(app, users=[("alice", "pw-alice"), ("bob", "pw-bob")])
    async for client in _client(app):
        login = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "pw-alice"}
        )
        access = login.json()["access_token"]
        response = await client.post(
            "/api/v1/auth/me/username",
            headers={"Authorization": f"Bearer {access}"},
            json={"current_password": "pw-alice", "new_username": "bob"},
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_change_username_same_value_is_noop(app: FastAPI) -> None:
    await _seed(app, users=[("alice", "pw-alice")])
    async for client in _client(app):
        login = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "pw-alice"}
        )
        access = login.json()["access_token"]
        response = await client.post(
            "/api/v1/auth/me/username",
            headers={"Authorization": f"Bearer {access}"},
            json={"current_password": "pw-alice", "new_username": "alice"},
        )
        assert response.status_code == 200
        assert response.json()["username"] == "alice"


@pytest.mark.asyncio
async def test_change_username_requires_authentication(app: FastAPI) -> None:
    await _seed(app, users=[("alice", "pw-alice")])
    async for client in _client(app):
        response = await client.post(
            "/api/v1/auth/me/username",
            json={"current_password": "x", "new_username": "alice2"},
        )
    assert response.status_code == 401

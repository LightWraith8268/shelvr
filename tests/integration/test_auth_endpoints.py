"""Integration tests for /api/v1/auth/{login,refresh,logout}."""

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
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    return create_app()


async def _seed_user(
    app: FastAPI,
    *,
    username: str = "alice",
    password: str = "hunter2",
    role: str = "reader",
    is_active: bool = True,
) -> int:
    """Create the schema in the in-memory DB and insert a user. Return its id."""
    from shelvr.db.base import Base

    engine = app.state.engine
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = app.state.session_factory
    async with factory() as session:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def _client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_login_returns_token_pair(app: FastAPI) -> None:
    await _seed_user(app)
    async for client in _client(app):
        response = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "hunter2"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(app: FastAPI) -> None:
    await _seed_user(app)
    async for client in _client(app):
        response = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "WRONG"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_rejects_unknown_user(app: FastAPI) -> None:
    await _seed_user(app)
    async for client in _client(app):
        response = await client.post(
            "/api/v1/auth/login", json={"username": "nobody", "password": "anything"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_rejects_inactive_user(app: FastAPI) -> None:
    await _seed_user(app, is_active=False)
    async for client in _client(app):
        response = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "hunter2"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(app: FastAPI) -> None:
    await _seed_user(app)
    async for client in _client(app):
        login = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "hunter2"}
        )
        refresh_token = login.json()["refresh_token"]

        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 200
        body = response.json()
        assert body["access_token"]
        # Rotation: old refresh is now revoked, new one differs.
        assert body["refresh_token"] != refresh_token

        # Old refresh token must no longer work.
        replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert replay.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(app: FastAPI) -> None:
    """A valid access token must not be accepted at /auth/refresh."""
    await _seed_user(app)
    async for client in _client(app):
        login = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "hunter2"}
        )
        access = login.json()["access_token"]
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_garbage(app: FastAPI) -> None:
    await _seed_user(app)
    async for client in _client(app):
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh(app: FastAPI) -> None:
    await _seed_user(app)
    async for client in _client(app):
        login = await client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "hunter2"}
        )
        refresh_token = login.json()["refresh_token"]

        logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert logout.status_code == 204

        replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert replay.status_code == 401


@pytest.mark.asyncio
async def test_logout_garbage_token_silent(app: FastAPI) -> None:
    """Logout must not leak whether a token was ever valid."""
    await _seed_user(app)
    async for client in _client(app):
        response = await client.post("/api/v1/auth/logout", json={"refresh_token": "garbage"})
        assert response.status_code == 204


@pytest.mark.asyncio
async def test_login_touches_last_login_at(app: FastAPI) -> None:
    user_id = await _seed_user(app)
    async for client in _client(app):
        await client.post("/api/v1/auth/login", json={"username": "alice", "password": "hunter2"})

    factory = app.state.session_factory
    async with factory() as session:  # type: AsyncSession
        user = await session.get(User, user_id)
        assert user is not None
        assert user.last_login_at is not None

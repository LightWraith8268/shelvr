"""Integration tests for /api/v1/books/{id}/sync (Readium Locator)."""

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
    from shelvr.db.models import Book, User
    from shelvr.main import create_app

    test_app = create_app()
    async with test_app.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_app.state.session_factory() as session:
        user = User(id=1, username="reader", password_hash="x", role="reader", is_active=True)
        book = Book(id=1, title="Book")
        session.add_all([user, book])
        await session.commit()

    user_obj = User(id=1, username="reader", password_hash="x", role="reader", is_active=True)
    test_app.dependency_overrides[get_current_user] = lambda: user_obj
    test_app.dependency_overrides[require_admin] = lambda: user_obj
    return test_app


@pytest.mark.asyncio
async def test_get_sync_returns_null_when_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/books/1/sync")
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_put_sync_then_get_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        put = await client.put(
            "/api/v1/books/1/sync",
            json={
                "locations": {
                    "totalProgression": 0.42,
                    "fragment": ["epubcfi(/6/8)"],
                },
            },
        )
        assert put.status_code == 200
        body = put.json()
        assert body["locations"]["fragment"] == ["epubcfi(/6/8)"]
        assert body["locations"]["totalProgression"] == pytest.approx(0.42)

        got = await client.get("/api/v1/books/1/sync")
        assert got.status_code == 200
        got_body = got.json()
        assert got_body["locations"]["fragment"] == ["epubcfi(/6/8)"]


@pytest.mark.asyncio
async def test_put_sync_falls_back_to_progression(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(
            "/api/v1/books/1/sync",
            json={
                "locations": {
                    "progression": 0.1,
                    "fragment": ["x"],
                },
            },
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_put_sync_requires_fragment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(
            "/api/v1/books/1/sync",
            json={"locations": {"totalProgression": 0.5}},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_put_sync_requires_progression(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(
            "/api/v1/books/1/sync",
            json={"locations": {"fragment": ["x"]}},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_sync_404_for_unknown_book(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        got = await client.get("/api/v1/books/9999/sync")
        assert got.status_code == 404
        put = await client.put(
            "/api/v1/books/9999/sync",
            json={"locations": {"totalProgression": 0.1, "fragment": ["x"]}},
        )
        assert put.status_code == 404


@pytest.mark.asyncio
async def test_get_sync_reflects_progress_set_via_progress_endpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Locator and progress endpoints share the same backing row."""
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.put(
            "/api/v1/books/1/progress",
            json={"locator": "epubcfi(/6/4)", "percent": 0.3},
        )
        got = await client.get("/api/v1/books/1/sync")
        body = got.json()
        assert body["locations"]["fragment"] == ["epubcfi(/6/4)"]
        assert body["locations"]["totalProgression"] == pytest.approx(0.3)

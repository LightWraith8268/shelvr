"""Integration tests for /api/v1/books/{id}/progress."""

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
        book = Book(id=1, title="Test Book")
        session.add_all([user, book])
        await session.commit()

    user_obj = User(id=1, username="reader", password_hash="x", role="reader", is_active=True)
    test_app.dependency_overrides[get_current_user] = lambda: user_obj
    test_app.dependency_overrides[require_admin] = lambda: user_obj
    return test_app


@pytest.mark.asyncio
async def test_get_progress_returns_null_when_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/books/1/progress")
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_put_progress_creates_then_updates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.put(
            "/api/v1/books/1/progress",
            json={"locator": "epubcfi(/6/4)", "percent": 0.25},
        )
        assert first.status_code == 200
        body = first.json()
        assert body["percent"] == pytest.approx(0.25)
        assert body["locator"] == "epubcfi(/6/4)"

        second = await client.put(
            "/api/v1/books/1/progress",
            json={"locator": "epubcfi(/6/8)", "percent": 0.5},
        )
        assert second.status_code == 200
        assert second.json()["percent"] == pytest.approx(0.5)

        latest = await client.get("/api/v1/books/1/progress")
        assert latest.json()["locator"] == "epubcfi(/6/8)"


@pytest.mark.asyncio
async def test_put_progress_rejects_out_of_range_percent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(
            "/api/v1/books/1/progress", json={"locator": "x", "percent": 1.5}
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_progress(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.put(
            "/api/v1/books/1/progress",
            json={"locator": "epubcfi(/6/4)", "percent": 0.25},
        )
        deleted = await client.delete("/api/v1/books/1/progress")
        assert deleted.status_code == 204

        after = await client.get("/api/v1/books/1/progress")
        assert after.json() is None


@pytest.mark.asyncio
async def test_progress_404_for_unknown_book(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/books/9999/progress")
    assert response.status_code == 404

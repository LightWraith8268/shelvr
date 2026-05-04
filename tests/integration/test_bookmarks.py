"""Integration tests for /api/v1/books/{id}/bookmarks and /auth/me/bookmarks."""

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
        book_one = Book(id=1, title="Book One")
        book_two = Book(id=2, title="Book Two")
        session.add_all([user, book_one, book_two])
        await session.commit()

    user_obj = User(id=1, username="reader", password_hash="x", role="reader", is_active=True)
    test_app.dependency_overrides[get_current_user] = lambda: user_obj
    test_app.dependency_overrides[require_admin] = lambda: user_obj
    return test_app


@pytest.mark.asyncio
async def test_create_and_list_bookmarks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post(
            "/api/v1/books/1/bookmarks",
            json={"locator": "epubcfi(/6/4)", "label": "Chapter 1"},
        )
        assert first.status_code == 201
        first_body = first.json()
        assert first_body["locator"] == "epubcfi(/6/4)"
        assert first_body["label"] == "Chapter 1"
        assert first_body["book_id"] == 1

        second = await client.post(
            "/api/v1/books/1/bookmarks",
            json={"locator": "epubcfi(/6/8)", "label": None},
        )
        assert second.status_code == 201

        listed = await client.get("/api/v1/books/1/bookmarks")
        assert listed.status_code == 200
        items = listed.json()
        assert len(items) == 2
        assert items[0]["locator"] == "epubcfi(/6/4)"
        assert items[1]["locator"] == "epubcfi(/6/8)"


@pytest.mark.asyncio
async def test_delete_bookmark(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/v1/books/1/bookmarks", json={"locator": "x", "label": "y"}
        )
        bookmark_id = created.json()["id"]
        deleted = await client.delete(f"/api/v1/books/1/bookmarks/{bookmark_id}")
        assert deleted.status_code == 204

        after = await client.get("/api/v1/books/1/bookmarks")
        assert after.json() == []

        # Idempotent: second delete reports 404, doesn't crash.
        again = await client.delete(f"/api/v1/books/1/bookmarks/{bookmark_id}")
        assert again.status_code == 404


@pytest.mark.asyncio
async def test_delete_bookmark_rejects_mismatched_book(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/v1/books/1/bookmarks", json={"locator": "x", "label": None}
        )
        bookmark_id = created.json()["id"]
        # Bookmark belongs to book 1, attempt delete via book 2's URL.
        wrong = await client.delete(f"/api/v1/books/2/bookmarks/{bookmark_id}")
        assert wrong.status_code == 404


@pytest.mark.asyncio
async def test_bookmarks_404_for_unknown_book(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        listed = await client.get("/api/v1/books/9999/bookmarks")
        assert listed.status_code == 404
        created = await client.post(
            "/api/v1/books/9999/bookmarks", json={"locator": "x", "label": None}
        )
        assert created.status_code == 404


@pytest.mark.asyncio
async def test_me_bookmarks_returns_cross_book(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/api/v1/books/1/bookmarks", json={"locator": "a", "label": "A"})
        await client.post("/api/v1/books/2/bookmarks", json={"locator": "b", "label": "B"})
        listed = await client.get("/api/v1/auth/me/bookmarks")
        assert listed.status_code == 200
        items = listed.json()["items"]
        assert {item["book_id"] for item in items} == {1, 2}

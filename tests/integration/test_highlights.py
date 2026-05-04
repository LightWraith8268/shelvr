"""Integration tests for /api/v1/books/{id}/highlights."""

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
async def test_create_and_list_highlights(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/v1/books/1/highlights",
            json={
                "locator_range": "epubcfi(/6/4!/4/2,/4/2/1:0,/4/2/1:50)",
                "text": "It was the best of times.",
                "color": "yellow",
                "note": "opening line",
            },
        )
        assert created.status_code == 201
        body = created.json()
        assert body["color"] == "yellow"
        assert body["note"] == "opening line"
        assert body["text"] == "It was the best of times."

        listed = await client.get("/api/v1/books/1/highlights")
        assert listed.status_code == 200
        items = listed.json()
        assert len(items) == 1
        assert items[0]["locator_range"].startswith("epubcfi(")


@pytest.mark.asyncio
async def test_update_highlight_color_and_clear_note(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/v1/books/1/highlights",
            json={"locator_range": "x", "text": "y", "color": "yellow", "note": "n"},
        )
        highlight_id = created.json()["id"]
        recolored = await client.patch(
            f"/api/v1/books/1/highlights/{highlight_id}", json={"color": "green"}
        )
        assert recolored.status_code == 200
        assert recolored.json()["color"] == "green"
        assert recolored.json()["note"] == "n"

        cleared = await client.patch(
            f"/api/v1/books/1/highlights/{highlight_id}", json={"clear_note": True}
        )
        assert cleared.status_code == 200
        assert cleared.json()["note"] is None


@pytest.mark.asyncio
async def test_delete_highlight_and_book_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/v1/books/1/highlights",
            json={"locator_range": "x", "text": "y", "color": "yellow", "note": None},
        )
        highlight_id = created.json()["id"]
        wrong = await client.delete(f"/api/v1/books/2/highlights/{highlight_id}")
        assert wrong.status_code == 404
        deleted = await client.delete(f"/api/v1/books/1/highlights/{highlight_id}")
        assert deleted.status_code == 204
        again = await client.delete(f"/api/v1/books/1/highlights/{highlight_id}")
        assert again.status_code == 404


@pytest.mark.asyncio
async def test_create_highlight_rejects_unknown_color(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/books/1/highlights",
            json={"locator_range": "x", "text": "y", "color": "purple", "note": None},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_highlights_404_for_unknown_book(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        listed = await client.get("/api/v1/books/9999/highlights")
        assert listed.status_code == 404
        created = await client.post(
            "/api/v1/books/9999/highlights",
            json={"locator_range": "x", "text": "y", "color": "yellow", "note": None},
        )
        assert created.status_code == 404

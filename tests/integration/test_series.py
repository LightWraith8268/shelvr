"""Integration tests for series resolution and the series facet."""

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
    from shelvr.db.models import Book, Series, User
    from shelvr.main import create_app

    test_app = create_app()
    async with test_app.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    fake_admin = User(id=1, username="admin", password_hash="x", role="admin", is_active=True)
    test_app.dependency_overrides[get_current_user] = lambda: fake_admin
    test_app.dependency_overrides[require_admin] = lambda: fake_admin

    # Seed: 3 books in 2 series.
    async with test_app.state.session_factory() as session:
        wheel = Series(name="The Wheel of Time", sort_name="Wheel of Time, The")
        gulliver = Series(name="Gulliver's Travels", sort_name="Gulliver's Travels")
        session.add_all([wheel, gulliver])
        await session.flush()

        session.add_all(
            [
                Book(title="The Eye of the World", series_id=wheel.id, series_index=1),
                Book(title="The Great Hunt", series_id=wheel.id, series_index=2),
                Book(title="Solo Book"),
            ]
        )
        await session.commit()

    return test_app


@pytest.mark.asyncio
async def test_series_facet_returns_counts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/series")
    assert response.status_code == 200
    items = response.json()["items"]
    counts = {item["name"]: item["count"] for item in items}
    assert counts == {"The Wheel of Time": 2}


@pytest.mark.asyncio
async def test_filter_books_by_series_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        series = await client.get("/api/v1/series")
        wheel_id = next(
            item["id"] for item in series.json()["items"] if item["name"] == "The Wheel of Time"
        )

        response = await client.get(f"/api/v1/books?series_id={wheel_id}&sort=series")
    body = response.json()
    titles = [book["title"] for book in body["items"]]
    assert titles == ["The Eye of the World", "The Great Hunt"]


@pytest.mark.asyncio
async def test_book_detail_includes_series_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        listing = await client.get("/api/v1/books?sort=title")
        wheel_book = next(
            item for item in listing.json()["items"] if item["title"] == "The Eye of the World"
        )
        detail = await client.get(f"/api/v1/books/{wheel_book['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["series"] == "The Wheel of Time"
    assert body["series_index"] == 1


@pytest.mark.asyncio
async def test_patch_book_sets_and_clears_series(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        listing = await client.get("/api/v1/books?sort=title")
        solo = next(item for item in listing.json()["items"] if item["title"] == "Solo Book")
        assert solo["series"] is None

        attach = await client.patch(
            f"/api/v1/books/{solo['id']}", json={"series": "Brand New Series"}
        )
        assert attach.status_code == 200
        assert attach.json()["series"] == "Brand New Series"

        clear = await client.patch(f"/api/v1/books/{solo['id']}", json={"series": None})
        assert clear.status_code == 200
        assert clear.json()["series"] is None


@pytest.mark.asyncio
async def test_series_facet_requires_authentication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from shelvr.db.base import Base
    from shelvr.main import create_app

    test_app = create_app()
    async with test_app.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/series")
    assert response.status_code == 401

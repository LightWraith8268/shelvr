"""Integration tests for facet endpoints and book filtering."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


async def _setup_app(monkeypatch, tmp_path):
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from shelvr.auth.deps import get_current_user, require_admin
    from shelvr.db.base import Base
    from shelvr.db.models import Author, Book, Tag, User
    from shelvr.db.models.book import book_authors, book_tags
    from shelvr.main import create_app

    test_app = create_app()
    async with test_app.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    fake_admin = User(
        id=1, username="admin", password_hash="x", role="admin", is_active=True
    )
    test_app.dependency_overrides[get_current_user] = lambda: fake_admin
    test_app.dependency_overrides[require_admin] = lambda: fake_admin

    # Seed: 3 books, 2 authors, 2 tags, 2 languages.
    async with test_app.state.session_factory() as session:
        swift = Author(name="Jonathan Swift", sort_name="Swift, Jonathan")
        austen = Author(name="Jane Austen", sort_name="Austen, Jane")
        satire = Tag(name="satire")
        classics = Tag(name="classics")
        session.add_all([swift, austen, satire, classics])
        await session.flush()

        proposal = Book(title="A Modest Proposal", language="en")
        gulliver = Book(title="Gulliver's Travels", language="en")
        emma = Book(title="Emma", language="fr")
        session.add_all([proposal, gulliver, emma])
        await session.flush()

        for book_id, author_ids in [
            (proposal.id, [swift.id]),
            (gulliver.id, [swift.id]),
            (emma.id, [austen.id]),
        ]:
            for author_id in author_ids:
                await session.execute(
                    book_authors.insert().values(book_id=book_id, author_id=author_id)
                )

        for book_id, tag_ids in [
            (proposal.id, [satire.id, classics.id]),
            (gulliver.id, [satire.id, classics.id]),
            (emma.id, [classics.id]),
        ]:
            for tag_id in tag_ids:
                await session.execute(
                    book_tags.insert().values(book_id=book_id, tag_id=tag_id)
                )

        await session.commit()

    return test_app


@pytest.mark.asyncio
async def test_tags_facet_returns_counts_descending(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/tags")
    assert response.status_code == 200
    items = response.json()["items"]
    counts = {item["name"]: item["count"] for item in items}
    assert counts == {"classics": 3, "satire": 2}
    # First item is the most-used tag.
    assert items[0]["name"] == "classics"


@pytest.mark.asyncio
async def test_authors_facet_returns_counts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/authors")
    assert response.status_code == 200
    items = response.json()["items"]
    counts = {item["name"]: item["count"] for item in items}
    assert counts == {"Jonathan Swift": 2, "Jane Austen": 1}


@pytest.mark.asyncio
async def test_languages_facet_returns_counts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/languages")
    assert response.status_code == 200
    items = response.json()["items"]
    counts = {item["code"]: item["count"] for item in items}
    assert counts == {"en": 2, "fr": 1}


@pytest.mark.asyncio
async def test_filter_books_by_tag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/books?tag=satire")
    assert response.status_code == 200
    body = response.json()
    titles = sorted(book["title"] for book in body["items"])
    assert titles == ["A Modest Proposal", "Gulliver's Travels"]


@pytest.mark.asyncio
async def test_filter_books_by_author_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Look up Jane Austen's id from the authors facet.
        authors = await client.get("/api/v1/authors")
        austen_id = next(
            item["id"] for item in authors.json()["items"] if item["name"] == "Jane Austen"
        )

        response = await client.get(f"/api/v1/books?author_id={austen_id}")
    titles = [book["title"] for book in response.json()["items"]]
    assert titles == ["Emma"]


@pytest.mark.asyncio
async def test_filter_books_by_language(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/books?language=fr")
    titles = [book["title"] for book in response.json()["items"]]
    assert titles == ["Emma"]


@pytest.mark.asyncio
async def test_combined_filters_intersect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """tag=satire AND language=en should match both Swift books, exclude Emma."""
    test_app = await _setup_app(monkeypatch, tmp_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/books?tag=satire&language=en")
    body = response.json()
    assert body["total"] == 2


@pytest.mark.asyncio
async def test_facets_require_authentication(
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
        for path in ("/api/v1/tags", "/api/v1/authors", "/api/v1/languages"):
            response = await client.get(path)
            assert response.status_code == 401, path

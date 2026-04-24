"""Integration test for POST /api/v1/books."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "books"


async def _setup_app(monkeypatch, tmp_path, library_path):
    """Create an app bound to an in-memory DB with schema created."""
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(library_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from shelvr.db.base import Base
    from shelvr.main import create_app

    test_app = create_app()
    engine = test_app.state.engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return test_app


@pytest.mark.asyncio
async def test_post_books_uploads_epub(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    """POST /api/v1/books with a multipart file creates a book."""
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)

    epub_fixture = FIXTURE_DIR / "modest-proposal.epub"
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with epub_fixture.open("rb") as upload_stream:
            response = await client.post(
                "/api/v1/books",
                files={"file": ("modest-proposal.epub", upload_stream, "application/epub+zip")},
            )

    assert response.status_code in (200, 201), response.text
    body = response.json()
    assert body["title"]
    assert any("swift" in a["name"].lower() for a in body["authors"])
    assert len(body["formats"]) == 1
    assert body["formats"][0]["format"] == "epub"


@pytest.mark.asyncio
async def test_post_books_dedup_returns_200(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    """Uploading the same bytes twice returns the existing book with 200."""
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)

    epub_fixture = FIXTURE_DIR / "modest-proposal.epub"
    epub_bytes = epub_fixture.read_bytes()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_response = await client.post(
            "/api/v1/books",
            files={"file": ("modest-proposal.epub", epub_bytes, "application/epub+zip")},
        )
        second_response = await client.post(
            "/api/v1/books",
            files={"file": ("renamed.epub", epub_bytes, "application/epub+zip")},
        )

    assert first_response.status_code in (200, 201)
    assert second_response.status_code == 200
    assert first_response.json()["id"] == second_response.json()["id"]


@pytest.mark.asyncio
async def test_get_books_list_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    """GET /api/v1/books on an empty library returns empty page."""
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/books")

    assert response.status_code == 200
    body = response.json()
    assert body == {"items": [], "total": 0, "limit": 50, "offset": 0}


@pytest.mark.asyncio
async def test_get_books_list_pagination_sort_search(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    """GET /api/v1/books supports limit/offset, sort=title, and q="""
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from shelvr.repositories.books import BookRepository
    from shelvr.schemas.book import BookCreate

    session_factory: async_sessionmaker = test_app.state.session_factory
    async with session_factory() as setup_session:
        repo = BookRepository(setup_session)
        await repo.create_from_metadata(
            BookCreate(title="Zebra Book", authors=["Alice Adams"]), cover_path=None
        )
        await repo.create_from_metadata(
            BookCreate(title="Apple Book", authors=["Bob Baker"]), cover_path=None
        )
        await repo.create_from_metadata(
            BookCreate(title="Cherry Pie", authors=["Alice Adams"]), cover_path=None
        )
        await setup_session.commit()

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Default sort = added desc — most recently inserted first
        default_response = await client.get("/api/v1/books")
        assert default_response.status_code == 200
        default_body = default_response.json()
        assert default_body["total"] == 3
        assert default_body["items"][0]["title"] == "Cherry Pie"

        # sort=title
        title_response = await client.get("/api/v1/books?sort=title")
        assert [b["title"] for b in title_response.json()["items"]] == [
            "Apple Book",
            "Cherry Pie",
            "Zebra Book",
        ]

        # pagination
        page_response = await client.get("/api/v1/books?sort=title&limit=1&offset=1")
        page_body = page_response.json()
        assert page_body["total"] == 3
        assert page_body["limit"] == 1
        assert page_body["offset"] == 1
        assert [b["title"] for b in page_body["items"]] == ["Cherry Pie"]

        # q matches title
        q_title_response = await client.get("/api/v1/books?q=zebra")
        assert [b["title"] for b in q_title_response.json()["items"]] == ["Zebra Book"]

        # q matches author
        q_author_response = await client.get("/api/v1/books?q=alice")
        q_author_titles = {b["title"] for b in q_author_response.json()["items"]}
        assert q_author_titles == {"Zebra Book", "Cherry Pie"}


@pytest.mark.asyncio
async def test_get_books_rejects_invalid_sort(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    """sort must be one of title|added."""
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/books?sort=bogus")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_books_rejects_unknown_extension(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    """POST with an unsupported extension returns 400."""
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/books",
            files={"file": ("readme.txt", b"not a book", "text/plain")},
        )

    assert response.status_code == 400

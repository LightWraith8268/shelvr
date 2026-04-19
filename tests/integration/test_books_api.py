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

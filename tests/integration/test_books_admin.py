"""Integration tests for PATCH and DELETE on /api/v1/books/{id}."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "books"


async def _setup_app(monkeypatch, tmp_path, library_path):
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(library_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from shelvr.auth.deps import get_current_user, require_admin
    from shelvr.db.base import Base
    from shelvr.db.models import User
    from shelvr.main import create_app

    test_app = create_app()
    engine = test_app.state.engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    fake_admin = User(id=1, username="test-admin", password_hash="x", role="admin", is_active=True)
    test_app.dependency_overrides[get_current_user] = lambda: fake_admin
    test_app.dependency_overrides[require_admin] = lambda: fake_admin
    return test_app


async def _upload(client: AsyncClient, fixture_name: str = "modest-proposal.epub") -> int:
    """Upload a fixture and return the book id."""
    body = (FIXTURE_DIR / fixture_name).read_bytes()
    response = await client.post(
        "/api/v1/books",
        files={"file": (fixture_name, body, "application/epub+zip")},
    )
    assert response.status_code in (200, 201), response.text
    book_id: int = response.json()["id"]
    return book_id


@pytest.mark.asyncio
async def test_patch_book_updates_title_and_authors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        book_id = await _upload(client)

        response = await client.patch(
            f"/api/v1/books/{book_id}",
            json={
                "title": "A Modest Proposal",
                "authors": ["Jonathan Swift", "Editor X"],
                "rating": 9,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "A Modest Proposal"
        assert body["sort_title"] == "Modest Proposal, A"
        assert body["rating"] == 9
        author_names = [author["name"] for author in body["authors"]]
        assert author_names == ["Jonathan Swift", "Editor X"]


@pytest.mark.asyncio
async def test_patch_book_replaces_tags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        book_id = await _upload(client)

        response = await client.patch(
            f"/api/v1/books/{book_id}", json={"tags": ["satire", "classics"]}
        )
        assert response.status_code == 200
        tag_names = sorted(tag["name"] for tag in response.json()["tags"])
        assert tag_names == ["classics", "satire"]


@pytest.mark.asyncio
async def test_patch_book_clears_tags_with_empty_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        book_id = await _upload(client)
        response = await client.patch(f"/api/v1/books/{book_id}", json={"tags": []})
        assert response.status_code == 200
        assert response.json()["tags"] == []


@pytest.mark.asyncio
async def test_patch_book_404(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.patch("/api/v1/books/9999", json={"title": "x"})
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_book_rejects_empty_title(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        book_id = await _upload(client)
        response = await client.patch(f"/api/v1/books/{book_id}", json={"title": ""})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_book_removes_row_and_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        book_id = await _upload(client)

        # Confirm files exist on disk before delete.
        get_before = await client.get(f"/api/v1/books/{book_id}")
        format_path = library_path / get_before.json()["formats"][0]["file_path"]
        cover_path = library_path / get_before.json()["cover_path"]
        assert format_path.is_file()
        assert cover_path.is_file()

        delete_response = await client.delete(f"/api/v1/books/{book_id}")
        assert delete_response.status_code == 204

        # Row gone.
        get_after = await client.get(f"/api/v1/books/{book_id}")
        assert get_after.status_code == 404

        # Files cleaned up.
        assert not format_path.is_file()
        assert not cover_path.is_file()


@pytest.mark.asyncio
async def test_delete_book_404(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.delete("/api/v1/books/9999")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_bulk_delete_partitions_known_and_unknown_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_id = await _upload(client)

        response = await client.post("/api/v1/books/bulk-delete", json={"ids": [first_id, 9999]})
        assert response.status_code == 200
        body = response.json()
        assert body["deleted"] == [first_id]
        assert body["not_found"] == [9999]

        gone = await client.get(f"/api/v1/books/{first_id}")
        assert gone.status_code == 404


@pytest.mark.asyncio
async def test_bulk_delete_dedupes_and_cleans_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_id = await _upload(client)
        before = await client.get(f"/api/v1/books/{first_id}")
        format_path = library_path / before.json()["formats"][0]["file_path"]
        cover_path = library_path / before.json()["cover_path"]
        assert format_path.is_file()

        response = await client.post(
            "/api/v1/books/bulk-delete", json={"ids": [first_id, first_id, first_id]}
        )
        body = response.json()
        # Dedup: a single delete even though the id was repeated.
        assert body["deleted"] == [first_id]
        assert body["not_found"] == []
        assert not format_path.is_file()
        assert not cover_path.is_file()


@pytest.mark.asyncio
async def test_bulk_delete_rejects_empty_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/books/bulk-delete", json={"ids": []})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bulk_tag_adds_and_removes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        book_id = await _upload(client)
        # Seed a known starting tag set.
        await client.patch(
            f"/api/v1/books/{book_id}",
            json={"tags": ["satire", "classics"]},
        )

        response = await client.post(
            "/api/v1/books/bulk-tag",
            json={"ids": [book_id], "add": ["fiction"], "remove": ["satire"]},
        )
        assert response.status_code == 200
        assert response.json() == {"updated": [book_id], "not_found": []}

        detail = await client.get(f"/api/v1/books/{book_id}")
        tags = sorted(tag["name"] for tag in detail.json()["tags"])
        assert tags == ["classics", "fiction"]


@pytest.mark.asyncio
async def test_bulk_tag_dedupes_and_skips_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        book_id = await _upload(client)

        response = await client.post(
            "/api/v1/books/bulk-tag",
            json={
                "ids": [book_id, 9999],
                "add": ["fiction", "Fiction", "fiction"],
                "remove": [],
            },
        )
        body = response.json()
        assert body["updated"] == [book_id]
        assert body["not_found"] == [9999]

        detail = await client.get(f"/api/v1/books/{book_id}")
        # Dedup: only one fiction tag despite three add entries.
        fiction = [tag for tag in detail.json()["tags"] if tag["name"].lower() == "fiction"]
        assert len(fiction) == 1


@pytest.mark.asyncio
async def test_bulk_tag_requires_at_least_one_action(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    test_app = await _setup_app(monkeypatch, tmp_path, library_path)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        book_id = await _upload(client)
        response = await client.post(
            "/api/v1/books/bulk-tag",
            json={"ids": [book_id], "add": [], "remove": []},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_patch_and_delete_require_admin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, library_path: Path
) -> None:
    """Override get_current_user to a reader; require_admin must 403."""
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(library_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from shelvr.auth.deps import get_current_user, require_admin
    from shelvr.db.base import Base
    from shelvr.db.models import User
    from shelvr.main import create_app

    test_app = create_app()
    async with test_app.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    admin = User(id=1, username="admin", password_hash="x", role="admin", is_active=True)
    reader = User(id=2, username="reader", password_hash="x", role="reader", is_active=True)
    # Upload as admin first.
    test_app.dependency_overrides[get_current_user] = lambda: admin
    test_app.dependency_overrides[require_admin] = lambda: admin
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        book_id = await _upload(client)

    # Switch to reader; require_admin should now reject.
    from fastapi import HTTPException
    from fastapi import status as http_status

    def _raise_admin_required() -> User:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN, detail="admin role required"
        )

    test_app.dependency_overrides[get_current_user] = lambda: reader
    test_app.dependency_overrides[require_admin] = _raise_admin_required

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        patch_response = await client.patch(f"/api/v1/books/{book_id}", json={"title": "Nope"})
        assert patch_response.status_code == 403
        delete_response = await client.delete(f"/api/v1/books/{book_id}")
        assert delete_response.status_code == 403

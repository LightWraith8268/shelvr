"""Integration tests for the OPDS 1.2 catalog."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, BasicAuth

from shelvr.auth.passwords import hash_password
from shelvr.db.models import Author, Book, Format, Tag, User
from shelvr.db.models.book import book_authors, book_tags
from shelvr.main import create_app

ATOM_NS = "{http://www.w3.org/2005/Atom}"
OPDS_NAVIGATION = "application/atom+xml;profile=opds-catalog;kind=navigation"
OPDS_ACQUISITION = "application/atom+xml;profile=opds-catalog;kind=acquisition"


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FastAPI:
    monkeypatch.setenv("SHELVR_JWT_SECRET", "opds-secret")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    return create_app()


async def _seed(app: FastAPI, *, book_count: int = 1) -> int:
    """Create the schema, seed a reader user, and add ``book_count`` books.

    Returns the seeded user's id.
    """
    from shelvr.db.base import Base

    engine = app.state.engine
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with app.state.session_factory() as session:
        user = User(username="reader", password_hash=hash_password("pw"), role="reader")
        session.add(user)
        for index in range(book_count):
            book = Book(
                title=f"Book {index}",
                language="en",
                publisher="Test Press",
                description=f"Description for book {index}",
            )
            session.add(book)
            await session.flush()
            session.add(
                Format(
                    book_id=book.id,
                    format="epub",
                    file_path=f"book-{index}.epub",
                    file_size=1024,
                    file_hash=f"hash{index}",
                    source="test",
                )
            )
        await session.commit()
        await session.refresh(user)
        return user.id


async def _client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_opds_root_requires_auth(app: FastAPI) -> None:
    await _seed(app)
    async for client in _client(app):
        response = await client.get("/api/v1/opds")
        assert response.status_code == 401
        assert "Basic" in response.headers["www-authenticate"]


@pytest.mark.asyncio
async def test_opds_root_basic_auth(app: FastAPI) -> None:
    await _seed(app)
    async for client in _client(app):
        response = await client.get("/api/v1/opds", auth=BasicAuth("reader", "pw"))
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(OPDS_NAVIGATION)

        root = ET.fromstring(response.content)
        assert root.tag == f"{ATOM_NS}feed"
        title = root.find(f"{ATOM_NS}title")
        assert title is not None and title.text == "Shelvr"
        entries = root.findall(f"{ATOM_NS}entry")
        # Root navigation surfaces "All books" plus "Browse by tag" / "Browse by author".
        assert len(entries) == 3
        subsection_hrefs = [
            entry.find(f"{ATOM_NS}link[@rel='subsection']").attrib["href"] for entry in entries
        ]
        assert any(href.endswith("/api/v1/opds/all") for href in subsection_hrefs)
        assert any(href.endswith("/api/v1/opds/by-tag") for href in subsection_hrefs)
        assert any(href.endswith("/api/v1/opds/by-author") for href in subsection_hrefs)


@pytest.mark.asyncio
async def test_opds_root_rejects_wrong_basic_password(app: FastAPI) -> None:
    await _seed(app)
    async for client in _client(app):
        response = await client.get("/api/v1/opds", auth=BasicAuth("reader", "WRONG"))
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_opds_all_lists_books(app: FastAPI) -> None:
    await _seed(app, book_count=2)
    async for client in _client(app):
        response = await client.get("/api/v1/opds/all", auth=BasicAuth("reader", "pw"))
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(OPDS_ACQUISITION)

        root = ET.fromstring(response.content)
        entries = root.findall(f"{ATOM_NS}entry")
        assert len(entries) == 2
        for entry in entries:
            acquisition = entry.find(f"{ATOM_NS}link[@rel='http://opds-spec.org/acquisition']")
            assert acquisition is not None
            assert acquisition.attrib["type"] == "application/epub+zip"


@pytest.mark.asyncio
async def test_opds_all_paginates(app: FastAPI) -> None:
    """Page size 25; 26 books → page=1 has next link, page=2 has previous."""
    await _seed(app, book_count=26)
    async for client in _client(app):
        first_page = await client.get("/api/v1/opds/all?page=1", auth=BasicAuth("reader", "pw"))
        first_root = ET.fromstring(first_page.content)
        assert first_root.find(f"{ATOM_NS}link[@rel='next']") is not None
        assert len(first_root.findall(f"{ATOM_NS}entry")) == 25

        second_page = await client.get("/api/v1/opds/all?page=2", auth=BasicAuth("reader", "pw"))
        second_root = ET.fromstring(second_page.content)
        assert second_root.find(f"{ATOM_NS}link[@rel='previous']") is not None
        assert len(second_root.findall(f"{ATOM_NS}entry")) == 1


async def _seed_with_facets(app: FastAPI) -> None:
    """Seed two books, one tag (satire) on both, one author (Swift) on both."""
    from shelvr.db.base import Base

    engine = app.state.engine
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with app.state.session_factory() as session:
        user = User(username="reader", password_hash=hash_password("pw"), role="reader")
        swift = Author(name="Jonathan Swift", sort_name="Swift, Jonathan")
        satire = Tag(name="satire")
        session.add_all([user, swift, satire])
        await session.flush()

        for index in range(2):
            book = Book(title=f"Book {index}", language="en")
            session.add(book)
            await session.flush()
            session.add(
                Format(
                    book_id=book.id,
                    format="epub",
                    file_path=f"book-{index}.epub",
                    file_size=1024,
                    file_hash=f"hash{index}",
                    source="test",
                )
            )
            await session.execute(book_authors.insert().values(book_id=book.id, author_id=swift.id))
            await session.execute(book_tags.insert().values(book_id=book.id, tag_id=satire.id))
        await session.commit()


@pytest.mark.asyncio
async def test_opds_by_tag_navigation(app: FastAPI) -> None:
    await _seed_with_facets(app)
    async for client in _client(app):
        response = await client.get("/api/v1/opds/by-tag", auth=BasicAuth("reader", "pw"))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(OPDS_NAVIGATION)
    root = ET.fromstring(response.content)
    titles = [entry.find(f"{ATOM_NS}title").text for entry in root.findall(f"{ATOM_NS}entry")]
    assert any("satire" in title for title in titles)


@pytest.mark.asyncio
async def test_opds_by_tag_acquisition_filters(app: FastAPI) -> None:
    await _seed_with_facets(app)
    async for client in _client(app):
        response = await client.get("/api/v1/opds/by-tag/satire", auth=BasicAuth("reader", "pw"))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(OPDS_ACQUISITION)
    root = ET.fromstring(response.content)
    entries = root.findall(f"{ATOM_NS}entry")
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_opds_by_author_navigation_and_acquisition(app: FastAPI) -> None:
    await _seed_with_facets(app)
    async for client in _client(app):
        navigation = await client.get("/api/v1/opds/by-author", auth=BasicAuth("reader", "pw"))
        nav_root = ET.fromstring(navigation.content)
        author_link = nav_root.find(f"{ATOM_NS}entry/{ATOM_NS}link[@rel='subsection']")
        assert author_link is not None
        author_href = author_link.attrib["href"]
        path = author_href.split("http://testserver", 1)[1]

        books_response = await client.get(path, auth=BasicAuth("reader", "pw"))
    assert books_response.status_code == 200
    books_root = ET.fromstring(books_response.content)
    assert len(books_root.findall(f"{ATOM_NS}entry")) == 2


@pytest.mark.asyncio
async def test_opds_acquisition_link_works_with_basic(app: FastAPI) -> None:
    """A KOReader-style flow: follow the acquisition link with Basic auth."""
    await _seed(app, book_count=1)
    async for client in _client(app):
        feed = await client.get("/api/v1/opds/all", auth=BasicAuth("reader", "pw"))
        root = ET.fromstring(feed.content)
        link = root.find(f"{ATOM_NS}entry/{ATOM_NS}link[@rel='http://opds-spec.org/acquisition']")
        assert link is not None
        href = link.attrib["href"]
        # The href is absolute; rip off the base for our in-process client.
        path = href.split("http://testserver", 1)[1]

        # The format file lives behind get_current_user, which now accepts
        # both Bearer and Basic. The OPDS reader's Basic credentials must
        # carry through to the download endpoint.
        download = await client.get(path, auth=BasicAuth("reader", "pw"))
        # 404 is expected — the seed format's file_path doesn't exist on
        # disk. What matters here is that auth passed (not 401).
        assert download.status_code != 401

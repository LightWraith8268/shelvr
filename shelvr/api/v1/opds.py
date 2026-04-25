"""OPDS 1.2 catalog endpoints.

Compat layer per the architecture doc: this is here so first-party-style
e-reader apps (KOReader, Moon+ Reader, Aldiko) can browse and download from
Shelvr without speaking the JSON API. New features must not land here first
— OPDS mirrors the existing data model only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.api.deps import get_session
from shelvr.auth.deps import get_current_user
from shelvr.db.models import Book, User
from shelvr.repositories.books import BookRepository

router = APIRouter(prefix="/opds", tags=["opds"])

ATOM_NS = "http://www.w3.org/2005/Atom"
DC_NS = "http://purl.org/dc/terms/"
OPDS_NS = "http://opds-spec.org/2010/catalog"

NAVIGATION_TYPE = "application/atom+xml;profile=opds-catalog;kind=navigation"
ACQUISITION_TYPE = "application/atom+xml;profile=opds-catalog;kind=acquisition"

# Smaller pages for OPDS — many e-reader clients render lists slowly.
OPDS_PAGE_SIZE = 25

_FORMAT_MIME = {
    "epub": "application/epub+zip",
    "pdf": "application/pdf",
    "mobi": "application/x-mobipocket-ebook",
    "azw3": "application/vnd.amazon.ebook",
}


def _register_namespaces() -> None:
    ET.register_namespace("", ATOM_NS)
    ET.register_namespace("dc", DC_NS)
    ET.register_namespace("opds", OPDS_NS)


_register_namespaces()


def _atom(name: str) -> str:
    return f"{{{ATOM_NS}}}{name}"


def _dc(name: str) -> str:
    return f"{{{DC_NS}}}{name}"


def _now_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _serialize(root: ET.Element) -> bytes:
    serialized: bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return serialized


def _xml_response(root: ET.Element, *, kind: str) -> Response:
    media_type = NAVIGATION_TYPE if kind == "navigation" else ACQUISITION_TYPE
    return Response(content=_serialize(root), media_type=media_type)


def _add_link(parent: ET.Element, *, rel: str, href: str, link_type: str) -> None:
    ET.SubElement(parent, _atom("link"), {"rel": rel, "href": href, "type": link_type})


def _build_feed(*, request: Request, feed_id: str, title: str, self_href: str) -> ET.Element:
    feed = ET.Element(_atom("feed"))
    ET.SubElement(feed, _atom("id")).text = feed_id
    ET.SubElement(feed, _atom("title")).text = title
    ET.SubElement(feed, _atom("updated")).text = _now_iso()
    base_url = str(request.base_url).rstrip("/")
    _add_link(feed, rel="self", href=f"{base_url}{self_href}", link_type=NAVIGATION_TYPE)
    _add_link(feed, rel="start", href=f"{base_url}/api/v1/opds", link_type=NAVIGATION_TYPE)
    return feed


def _build_root(request: Request) -> ET.Element:
    base_url = str(request.base_url).rstrip("/")
    feed = _build_feed(
        request=request,
        feed_id="urn:shelvr:opds:root",
        title="Shelvr",
        self_href="/api/v1/opds",
    )

    sections: list[tuple[str, str, str, str, str]] = [
        (
            "urn:shelvr:opds:all",
            "All books",
            "Every book in the library, newest first.",
            "/api/v1/opds/all",
            ACQUISITION_TYPE,
        ),
        (
            "urn:shelvr:opds:by-tag",
            "Browse by tag",
            "Tags grouped by usage.",
            "/api/v1/opds/by-tag",
            NAVIGATION_TYPE,
        ),
        (
            "urn:shelvr:opds:by-author",
            "Browse by author",
            "Authors grouped by usage.",
            "/api/v1/opds/by-author",
            NAVIGATION_TYPE,
        ),
    ]
    for entry_id, title, content, href, link_type in sections:
        entry = ET.SubElement(feed, _atom("entry"))
        ET.SubElement(entry, _atom("id")).text = entry_id
        ET.SubElement(entry, _atom("title")).text = title
        ET.SubElement(entry, _atom("updated")).text = _now_iso()
        ET.SubElement(entry, _atom("content"), {"type": "text"}).text = content
        _add_link(entry, rel="subsection", href=f"{base_url}{href}", link_type=link_type)
    return feed


def _book_entry(book: Book, base_url: str) -> ET.Element:
    entry = ET.Element(_atom("entry"))
    ET.SubElement(entry, _atom("id")).text = f"urn:shelvr:book:{book.id}"
    ET.SubElement(entry, _atom("title")).text = book.title
    ET.SubElement(entry, _atom("updated")).text = (
        book.date_modified.replace(microsecond=0).isoformat() + "Z"
    )

    for author in book.authors:
        author_element = ET.SubElement(entry, _atom("author"))
        ET.SubElement(author_element, _atom("name")).text = author.name

    if book.language:
        ET.SubElement(entry, _dc("language")).text = book.language
    if book.publisher:
        ET.SubElement(entry, _dc("publisher")).text = book.publisher
    if book.description:
        ET.SubElement(entry, _atom("summary"), {"type": "text"}).text = book.description

    if book.cover_path:
        cover_url = f"{base_url}/api/v1/books/{book.id}/cover?size=original"
        _add_link(entry, rel="http://opds-spec.org/image", href=cover_url, link_type="image/jpeg")
        thumb_url = f"{base_url}/api/v1/books/{book.id}/cover?size=small"
        _add_link(
            entry,
            rel="http://opds-spec.org/image/thumbnail",
            href=thumb_url,
            link_type="image/jpeg",
        )

    for book_format in book.formats:
        media_type = _FORMAT_MIME.get(book_format.format.lower(), "application/octet-stream")
        _add_link(
            entry,
            rel="http://opds-spec.org/acquisition",
            href=f"{base_url}/api/v1/formats/{book_format.id}/file",
            link_type=media_type,
        )

    return entry


@router.get("", response_class=Response)
async def opds_root(
    request: Request,
    _user: User = Depends(get_current_user),
) -> Response:
    """Root navigation feed listing the catalog's top-level shelves."""
    return _xml_response(_build_root(request), kind="navigation")


@router.get("/all", response_class=Response)
async def opds_all(
    request: Request,
    page: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> Response:
    """Acquisition feed: every book, paginated, newest first."""
    repo = BookRepository(session)
    offset = (page - 1) * OPDS_PAGE_SIZE
    books, total = await repo.list_books(
        limit=OPDS_PAGE_SIZE, offset=offset, sort="added", query=None
    )
    base_url = str(request.base_url).rstrip("/")

    feed = _build_feed(
        request=request,
        feed_id=f"urn:shelvr:opds:all:p{page}",
        title="All books",
        self_href=f"/api/v1/opds/all?page={page}",
    )

    last_page = max(1, (total + OPDS_PAGE_SIZE - 1) // OPDS_PAGE_SIZE)
    if page < last_page:
        _add_link(
            feed,
            rel="next",
            href=f"{base_url}/api/v1/opds/all?page={page + 1}",
            link_type=ACQUISITION_TYPE,
        )
    if page > 1:
        _add_link(
            feed,
            rel="previous",
            href=f"{base_url}/api/v1/opds/all?page={page - 1}",
            link_type=ACQUISITION_TYPE,
        )
    _add_link(
        feed,
        rel="first",
        href=f"{base_url}/api/v1/opds/all?page=1",
        link_type=ACQUISITION_TYPE,
    )
    _add_link(
        feed,
        rel="last",
        href=f"{base_url}/api/v1/opds/all?page={last_page}",
        link_type=ACQUISITION_TYPE,
    )

    for book in books:
        feed.append(_book_entry(book, base_url))

    return _xml_response(feed, kind="acquisition")


def _paginated_acquisition(
    request: Request,
    *,
    feed_id: str,
    title: str,
    self_path: str,
    page: int,
    total: int,
    books: list[Book],
) -> ET.Element:
    """Build an acquisition feed with first/last/next/previous links."""
    base_url = str(request.base_url).rstrip("/")
    feed = _build_feed(
        request=request,
        feed_id=f"{feed_id}:p{page}",
        title=title,
        self_href=f"{self_path}{'&' if '?' in self_path else '?'}page={page}",
    )
    last_page = max(1, (total + OPDS_PAGE_SIZE - 1) // OPDS_PAGE_SIZE)
    sep = "&" if "?" in self_path else "?"
    if page < last_page:
        _add_link(
            feed,
            rel="next",
            href=f"{base_url}{self_path}{sep}page={page + 1}",
            link_type=ACQUISITION_TYPE,
        )
    if page > 1:
        _add_link(
            feed,
            rel="previous",
            href=f"{base_url}{self_path}{sep}page={page - 1}",
            link_type=ACQUISITION_TYPE,
        )
    _add_link(
        feed,
        rel="first",
        href=f"{base_url}{self_path}{sep}page=1",
        link_type=ACQUISITION_TYPE,
    )
    _add_link(
        feed,
        rel="last",
        href=f"{base_url}{self_path}{sep}page={last_page}",
        link_type=ACQUISITION_TYPE,
    )
    for book in books:
        feed.append(_book_entry(book, base_url))
    return feed


@router.get("/by-tag", response_class=Response)
async def opds_tags(
    request: Request,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> Response:
    """Navigation feed listing every tag with its book count."""
    repo = BookRepository(session)
    rows = await repo.list_tags_with_counts()
    base_url = str(request.base_url).rstrip("/")
    feed = _build_feed(
        request=request,
        feed_id="urn:shelvr:opds:by-tag",
        title="Browse by tag",
        self_href="/api/v1/opds/by-tag",
    )
    for tag, count in rows:
        entry = ET.SubElement(feed, _atom("entry"))
        ET.SubElement(entry, _atom("id")).text = f"urn:shelvr:tag:{tag.id}"
        ET.SubElement(entry, _atom("title")).text = f"{tag.name} ({count})"
        ET.SubElement(entry, _atom("updated")).text = _now_iso()
        _add_link(
            entry,
            rel="subsection",
            href=f"{base_url}/api/v1/opds/by-tag/{tag.name}",
            link_type=ACQUISITION_TYPE,
        )
    return _xml_response(feed, kind="navigation")


@router.get("/by-tag/{tag_name}", response_class=Response)
async def opds_tag_books(
    tag_name: str,
    request: Request,
    page: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> Response:
    """Acquisition feed of every book carrying ``tag_name``."""
    repo = BookRepository(session)
    offset = (page - 1) * OPDS_PAGE_SIZE
    books, total = await repo.list_books(
        limit=OPDS_PAGE_SIZE, offset=offset, sort="added", query=None, tag=tag_name
    )
    feed = _paginated_acquisition(
        request,
        feed_id=f"urn:shelvr:opds:tag:{tag_name}",
        title=f"Tag: {tag_name}",
        self_path=f"/api/v1/opds/by-tag/{tag_name}",
        page=page,
        total=total,
        books=books,
    )
    return _xml_response(feed, kind="acquisition")


@router.get("/by-author", response_class=Response)
async def opds_authors(
    request: Request,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> Response:
    """Navigation feed listing every author with their book count."""
    repo = BookRepository(session)
    rows = await repo.list_authors_with_counts()
    base_url = str(request.base_url).rstrip("/")
    feed = _build_feed(
        request=request,
        feed_id="urn:shelvr:opds:by-author",
        title="Browse by author",
        self_href="/api/v1/opds/by-author",
    )
    for author, count in rows:
        entry = ET.SubElement(feed, _atom("entry"))
        ET.SubElement(entry, _atom("id")).text = f"urn:shelvr:author:{author.id}"
        ET.SubElement(entry, _atom("title")).text = f"{author.name} ({count})"
        ET.SubElement(entry, _atom("updated")).text = _now_iso()
        _add_link(
            entry,
            rel="subsection",
            href=f"{base_url}/api/v1/opds/by-author/{author.id}",
            link_type=ACQUISITION_TYPE,
        )
    return _xml_response(feed, kind="navigation")


@router.get("/by-author/{author_id}", response_class=Response)
async def opds_author_books(
    author_id: int,
    request: Request,
    page: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> Response:
    """Acquisition feed of every book by ``author_id``."""
    repo = BookRepository(session)
    offset = (page - 1) * OPDS_PAGE_SIZE
    books, total = await repo.list_books(
        limit=OPDS_PAGE_SIZE,
        offset=offset,
        sort="added",
        query=None,
        author_id=author_id,
    )
    feed = _paginated_acquisition(
        request,
        feed_id=f"urn:shelvr:opds:author:{author_id}",
        title=f"Author #{author_id}",
        self_path=f"/api/v1/opds/by-author/{author_id}",
        page=page,
        total=total,
        books=books,
    )
    return _xml_response(feed, kind="acquisition")

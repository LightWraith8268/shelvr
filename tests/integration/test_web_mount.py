"""Integration tests for the SPA static mount and fallback."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from shelvr.web import mount_web


def _build_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>Shelvr</title>", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('hi')", encoding="utf-8")
    return dist


@pytest.mark.asyncio
async def test_index_served_at_root(tmp_path: Path) -> None:
    app = FastAPI()
    mount_web(app, _build_dist(tmp_path))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "Shelvr" in response.text


@pytest.mark.asyncio
async def test_static_asset_served(tmp_path: Path) -> None:
    app = FastAPI()
    mount_web(app, _build_dist(tmp_path))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/assets/app.js")
    assert response.status_code == 200
    assert "console.log" in response.text


@pytest.mark.asyncio
async def test_unknown_path_falls_back_to_index(tmp_path: Path) -> None:
    """Client-side router paths must return index.html so React Router can route."""
    app = FastAPI()
    mount_web(app, _build_dist(tmp_path))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/books/42")
    assert response.status_code == 200
    assert "Shelvr" in response.text


@pytest.mark.asyncio
async def test_api_path_not_shadowed(tmp_path: Path) -> None:
    """The SPA fallback must never swallow /api/* — those should miss to the API router."""
    app = FastAPI()
    mount_web(app, _build_dist(tmp_path))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/missing")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_path_traversal_falls_back(tmp_path: Path) -> None:
    """A traversal attempt outside dist must not leak files; falls back to index."""
    app = FastAPI()
    mount_web(app, _build_dist(tmp_path))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/..%2Fsecret.txt")
    assert response.status_code == 200
    assert "Shelvr" in response.text


@pytest.mark.asyncio
async def test_missing_dist_dir_is_noop(tmp_path: Path) -> None:
    """Server should boot fine when web/dist/ doesn't exist (e.g. during early dev)."""
    app = FastAPI()
    mount_web(app, tmp_path / "does-not-exist")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")
    assert response.status_code == 404

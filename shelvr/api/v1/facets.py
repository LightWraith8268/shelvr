"""Facet endpoints — list tags / authors / languages with usage counts.

These power the Library UI's filter panel. Read-only and small enough to
return without pagination for the v1 single-user / homelab scale.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.api.deps import get_session
from shelvr.auth.deps import get_current_user
from shelvr.db.models import User
from shelvr.repositories.books import BookRepository

router = APIRouter(tags=["facets"])


@router.get("/tags")
async def list_tags(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    repo = BookRepository(session)
    rows = await repo.list_tags_with_counts()
    return {
        "items": [
            {"id": tag.id, "name": tag.name, "color": tag.color, "count": count}
            for tag, count in rows
        ]
    }


@router.get("/authors")
async def list_authors(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    repo = BookRepository(session)
    rows = await repo.list_authors_with_counts()
    return {
        "items": [
            {
                "id": author.id,
                "name": author.name,
                "sort_name": author.sort_name,
                "count": count,
            }
            for author, count in rows
        ]
    }


@router.get("/languages")
async def list_languages(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    repo = BookRepository(session)
    rows = await repo.list_languages_with_counts()
    return {"items": [{"code": code, "count": count} for code, count in rows]}


@router.get("/series")
async def list_series(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    repo = BookRepository(session)
    rows = await repo.list_series_with_counts()
    return {
        "items": [
            {
                "id": series.id,
                "name": series.name,
                "sort_name": series.sort_name,
                "count": count,
            }
            for series, count in rows
        ]
    }

"""Repository for per-user bookmarks within a book."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.db.models import Bookmark


class BookmarkRepository:
    """CRUD over the bookmarks table, scoped to a user."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_book(self, *, book_id: int, user_id: int) -> list[Bookmark]:
        statement = (
            select(Bookmark)
            .where(Bookmark.book_id == book_id, Bookmark.user_id == user_id)
            .order_by(Bookmark.created_at.asc(), Bookmark.id.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_for_user(self, *, user_id: int, limit: int = 100) -> list[Bookmark]:
        statement = (
            select(Bookmark)
            .where(Bookmark.user_id == user_id)
            .order_by(Bookmark.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get(self, *, bookmark_id: int, user_id: int) -> Bookmark | None:
        statement = select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == user_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self, *, book_id: int, user_id: int, locator: str, label: str | None
    ) -> Bookmark:
        bookmark = Bookmark(book_id=book_id, user_id=user_id, locator=locator, label=label)
        self._session.add(bookmark)
        await self._session.flush()
        await self._session.refresh(bookmark)
        return bookmark

    async def delete(self, *, bookmark_id: int, user_id: int) -> bool:
        existing = await self.get(bookmark_id=bookmark_id, user_id=user_id)
        if existing is None:
            return False
        await self._session.delete(existing)
        await self._session.flush()
        return True

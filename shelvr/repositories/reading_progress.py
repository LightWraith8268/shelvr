"""Repository for per-user reading progress."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.db.models import ReadingProgress


class ReadingProgressRepository:
    """Reads and upserts the (book_id, user_id) reading position."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, book_id: int, user_id: int) -> ReadingProgress | None:
        statement = select(ReadingProgress).where(
            ReadingProgress.book_id == book_id, ReadingProgress.user_id == user_id
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert(
        self, *, book_id: int, user_id: int, locator: str, percent: float
    ) -> ReadingProgress:
        existing = await self.get(book_id=book_id, user_id=user_id)
        if existing is None:
            row = ReadingProgress(
                book_id=book_id, user_id=user_id, locator=locator, percent=percent
            )
            self._session.add(row)
            await self._session.flush()
            await self._session.refresh(row)
            return row
        existing.locator = locator
        existing.percent = percent
        await self._session.flush()
        await self._session.refresh(existing)
        return existing

    async def delete(self, *, book_id: int, user_id: int) -> bool:
        existing = await self.get(book_id=book_id, user_id=user_id)
        if existing is None:
            return False
        await self._session.delete(existing)
        await self._session.flush()
        return True

    async def list_for_user(self, *, user_id: int) -> list[ReadingProgress]:
        statement = select(ReadingProgress).where(ReadingProgress.user_id == user_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_recent_for_user(
        self, *, user_id: int, limit: int = 12, exclude_finished: bool = True
    ) -> list[ReadingProgress]:
        """Return the user's most-recently-touched in-progress rows."""
        statement = select(ReadingProgress).where(ReadingProgress.user_id == user_id)
        if exclude_finished:
            statement = statement.where(ReadingProgress.percent < 1.0)
        statement = statement.order_by(ReadingProgress.updated_at.desc()).limit(limit)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

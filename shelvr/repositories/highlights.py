"""Repository for per-user EPUB highlights."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.db.models import Highlight


class HighlightRepository:
    """CRUD over the highlights table, scoped to a user."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_book(self, *, book_id: int, user_id: int) -> list[Highlight]:
        statement = (
            select(Highlight)
            .where(Highlight.book_id == book_id, Highlight.user_id == user_id)
            .order_by(Highlight.created_at.asc(), Highlight.id.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_for_user(self, *, user_id: int, limit: int = 100) -> list[Highlight]:
        statement = (
            select(Highlight)
            .where(Highlight.user_id == user_id)
            .order_by(Highlight.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get(self, *, highlight_id: int, user_id: int) -> Highlight | None:
        statement = select(Highlight).where(
            Highlight.id == highlight_id, Highlight.user_id == user_id
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        book_id: int,
        user_id: int,
        locator_range: str,
        text: str,
        color: str,
        note: str | None,
    ) -> Highlight:
        highlight = Highlight(
            book_id=book_id,
            user_id=user_id,
            locator_range=locator_range,
            text=text,
            color=color,
            note=note,
        )
        self._session.add(highlight)
        await self._session.flush()
        await self._session.refresh(highlight)
        return highlight

    async def update(
        self,
        *,
        highlight_id: int,
        user_id: int,
        color: str | None,
        note: str | None,
        clear_note: bool,
    ) -> Highlight | None:
        existing = await self.get(highlight_id=highlight_id, user_id=user_id)
        if existing is None:
            return None
        if color is not None:
            existing.color = color
        if clear_note:
            existing.note = None
        elif note is not None:
            existing.note = note
        await self._session.flush()
        await self._session.refresh(existing)
        return existing

    async def delete(self, *, highlight_id: int, user_id: int) -> bool:
        existing = await self.get(highlight_id=highlight_id, user_id=user_id)
        if existing is None:
            return False
        await self._session.delete(existing)
        await self._session.flush()
        return True

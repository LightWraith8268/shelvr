"""Repository for user accounts."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.db.models import User


class UserRepository:
    """All read and write operations on the ``users`` table go through here."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        statement = select(User).where(User.username == username)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        username: str,
        password_hash: str,
        role: str = "reader",
    ) -> User:
        user = User(username=username, password_hash=password_hash, role=role)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def touch_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(tz=UTC)
        await self._session.flush()

    async def update_password_hash(self, user: User, password_hash: str) -> None:
        """Replace the stored password hash for ``user``."""
        user.password_hash = password_hash
        await self._session.flush()

    async def update_username(self, user: User, new_username: str) -> None:
        """Replace the username for ``user``. Caller is responsible for uniqueness check."""
        user.username = new_username
        await self._session.flush()

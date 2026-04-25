"""Repository for the ``refresh_tokens`` table.

Refresh tokens are DB-backed so that logout can revoke a specific token
(by ``jti``) and so a server-wide reset can revoke every token issued for a
user. The token's bearer string is never stored — only its ``jti`` claim,
expiry, and revocation flag.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.db.models import RefreshToken


class RefreshTokenRepository:
    """All operations on issued refresh tokens go through here."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: int, jti: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(user_id=user_id, jti=jti, expires_at=expires_at)
        self._session.add(token)
        await self._session.flush()
        await self._session.refresh(token)
        return token

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke(self, jti: str) -> None:
        statement = update(RefreshToken).where(RefreshToken.jti == jti).values(revoked=True)
        await self._session.execute(statement)

    async def revoke_all_for_user(self, user_id: int) -> None:
        statement = update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True)
        await self._session.execute(statement)

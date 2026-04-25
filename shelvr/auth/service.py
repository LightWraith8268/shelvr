"""Authentication service — verifies credentials and issues tokens."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from shelvr.auth.passwords import verify_password
from shelvr.auth.tokens import IssuedRefreshToken, issue_access_token, issue_refresh_token
from shelvr.config import Settings
from shelvr.db.models import User
from shelvr.repositories.refresh_tokens import RefreshTokenRepository
from shelvr.repositories.users import UserRepository


@dataclass(frozen=True)
class TokenPair:
    """Bundle returned to clients after login or refresh."""

    access_token: str
    refresh_token: str
    refresh_jti: str
    refresh_expires_at: datetime


class AuthService:
    """Coordinates user lookup, password verification, and token issuance."""

    def __init__(
        self,
        *,
        settings: Settings,
        user_repo: UserRepository,
        refresh_repo: RefreshTokenRepository,
    ) -> None:
        self._settings = settings
        self._user_repo = user_repo
        self._refresh_repo = refresh_repo

    async def authenticate(self, *, username: str, password: str) -> User | None:
        """Return the User iff credentials match an active account."""
        user = await self._user_repo.get_by_username(username)
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def issue_token_pair(self, user: User) -> TokenPair:
        """Issue access + refresh tokens, persisting the refresh jti for revocation."""
        access = issue_access_token(
            user_id=user.id,
            role=user.role,
            secret=self._settings.jwt_secret,
            ttl_minutes=self._settings.jwt_access_ttl_minutes,
        )
        refresh: IssuedRefreshToken = issue_refresh_token(
            user_id=user.id,
            secret=self._settings.jwt_secret,
            ttl_days=self._settings.jwt_refresh_ttl_days,
        )
        await self._refresh_repo.create(
            user_id=user.id, jti=refresh.jti, expires_at=refresh.expires_at
        )
        await self._user_repo.touch_last_login(user)
        return TokenPair(
            access_token=access,
            refresh_token=refresh.token,
            refresh_jti=refresh.jti,
            refresh_expires_at=refresh.expires_at,
        )

    async def rotate_refresh_token(self, *, presented_jti: str, user: User) -> TokenPair:
        """Revoke the old refresh jti and issue a new pair (refresh-token rotation)."""
        await self._refresh_repo.revoke(presented_jti)
        return await self.issue_token_pair(user)

    async def is_refresh_token_valid(self, *, jti: str) -> bool:
        """Confirm the jti is on file, not revoked, and not expired."""
        token = await self._refresh_repo.get_by_jti(jti)
        if token is None or token.revoked:
            return False
        # Stored as naive UTC; compare against naive UTC now.
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        return token.expires_at > now

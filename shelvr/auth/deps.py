"""FastAPI dependencies that resolve the current authenticated user."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.api.deps import get_session, get_settings
from shelvr.auth.passwords import verify_password
from shelvr.auth.tokens import TokenError, decode_token
from shelvr.config import Settings
from shelvr.db.models import User
from shelvr.repositories.users import UserRepository

# auto_error=False so we can produce a uniform 401 with a WWW-Authenticate
# header rather than FastAPI's default 403 for missing auth.
_bearer_scheme = HTTPBearer(auto_error=False)
_basic_scheme = HTTPBasic(auto_error=False)

# Browser web flow uses Bearer; OPDS readers (KOReader, Moon+ Reader) speak
# Basic. Both auth modes resolve to the same users table, so we challenge
# Bearer first and let Basic clients fall back transparently.
_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="not authenticated",
    headers={"WWW-Authenticate": 'Bearer, Basic realm="Shelvr"'},
)


async def _resolve_bearer(
    credentials: HTTPAuthorizationCredentials,
    session: AsyncSession,
    settings: Settings,
) -> User | None:
    if credentials.scheme.lower() != "bearer":
        return None
    try:
        claims = decode_token(
            credentials.credentials, secret=settings.jwt_secret, expected_type="access"
        )
    except TokenError:
        return None
    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        return None
    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        return None
    return user


async def _resolve_basic(
    credentials: HTTPBasicCredentials,
    session: AsyncSession,
) -> User | None:
    user = await UserRepository(session).get_by_username(credentials.username)
    if user is None or not user.is_active:
        return None
    if not verify_password(credentials.password, user.password_hash):
        return None
    return user


async def get_current_user(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    basic: HTTPBasicCredentials | None = Depends(_basic_scheme),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    """Resolve the User identified by the request.

    Bearer JWT and HTTP Basic are both accepted — Bearer for the React UI,
    Basic for OPDS readers. Tests can sidestep this via
    ``app.dependency_overrides[get_current_user] = lambda: fake_user``.
    """
    user: User | None = None
    if bearer is not None:
        user = await _resolve_bearer(bearer, session, settings)
    if user is None and basic is not None:
        user = await _resolve_basic(basic, session)
    if user is None:
        raise _UNAUTHORIZED

    request.state.user = user
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that requires the authenticated user to have role=admin."""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")
    return user

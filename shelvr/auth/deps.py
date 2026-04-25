"""FastAPI dependencies that resolve the current authenticated user."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.api.deps import get_session, get_settings
from shelvr.auth.tokens import TokenError, decode_token
from shelvr.config import Settings
from shelvr.db.models import User
from shelvr.repositories.users import UserRepository

# auto_error=False so we can produce a uniform 401 with a WWW-Authenticate
# header rather than FastAPI's default 403 for missing auth.
_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    """Resolve the User identified by the request's bearer token.

    Tests can sidestep the real chain via
    ``app.dependency_overrides[get_current_user] = lambda: fake_user``.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _UNAUTHORIZED

    try:
        claims = decode_token(
            credentials.credentials, secret=settings.jwt_secret, expected_type="access"
        )
    except TokenError as exc:
        raise _UNAUTHORIZED from exc

    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _UNAUTHORIZED from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _UNAUTHORIZED

    request.state.user = user
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that requires the authenticated user to have role=admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="admin role required"
        )
    return user

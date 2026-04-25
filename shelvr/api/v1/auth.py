"""Authentication endpoints — login, refresh, logout, me."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shelvr.api.deps import get_session, get_settings
from shelvr.auth.deps import get_current_user
from shelvr.auth.service import AuthService
from shelvr.auth.tokens import TokenError, decode_token
from shelvr.config import Settings
from shelvr.db.models import User
from shelvr.repositories.refresh_tokens import RefreshTokenRepository
from shelvr.repositories.users import UserRepository
from shelvr.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])

CREDENTIAL_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="invalid credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def _build_service(session: AsyncSession, settings: Settings) -> AuthService:
    return AuthService(
        settings=settings,
        user_repo=UserRepository(session),
        refresh_repo=RefreshTokenRepository(session),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Exchange username + password for an access + refresh token pair."""
    service = _build_service(session, settings)
    user = await service.authenticate(username=body.username, password=body.password)
    if user is None:
        raise CREDENTIAL_ERROR
    pair = await service.issue_token_pair(user)
    await session.commit()
    return {"access_token": pair.access_token, "refresh_token": pair.refresh_token}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Trade a valid refresh token for a fresh access + refresh pair (rotation)."""
    try:
        claims = decode_token(
            body.refresh_token, secret=settings.jwt_secret, expected_type="refresh"
        )
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token"
        ) from exc

    service = _build_service(session, settings)
    jti = claims.get("jti")
    if not isinstance(jti, str) or not await service.is_refresh_token_valid(jti=jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token revoked or expired"
        )

    user_id = int(claims["sub"])
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user no longer active"
        )

    pair = await service.rotate_refresh_token(presented_jti=jti, user=user)
    await session.commit()
    return {"access_token": pair.access_token, "refresh_token": pair.refresh_token}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> None:
    """Revoke the presented refresh token. Idempotent — unknown tokens 204."""
    try:
        claims = decode_token(
            body.refresh_token, secret=settings.jwt_secret, expected_type="refresh"
        )
    except TokenError:
        # Don't leak whether a token was ever valid.
        return None
    jti = claims.get("jti")
    if isinstance(jti, str):
        repo = RefreshTokenRepository(session)
        await repo.revoke(jti)
        await session.commit()
    return None


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user."""
    return user

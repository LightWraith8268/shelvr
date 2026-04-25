"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Body for POST /auth/login."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=500)


class RefreshRequest(BaseModel):
    """Body for POST /auth/refresh."""

    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    """Body for POST /auth/logout."""

    refresh_token: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Returned by login and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    """Public-safe user shape — never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None

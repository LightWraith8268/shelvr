"""JWT issuance and decoding.

Two distinct token kinds. ``access`` tokens are short-lived (minutes), carry
the user's role, and gate API requests. ``refresh`` tokens are longer-lived
(days), carry a unique ``jti`` claim that is recorded in the
``refresh_tokens`` table so we can revoke specific tokens at logout time.

Both kinds are signed with HS256 using the shared ``jwt_secret`` from
settings. We don't ship asymmetric keys for v1 — every install holds the
secret locally and signs and verifies with the same key.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt

ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    """Raised when a JWT cannot be decoded, has the wrong type, or is expired."""


@dataclass(frozen=True)
class IssuedRefreshToken:
    """Bundle returned by :func:`issue_refresh_token` so callers can persist
    the ``jti`` and ``expires_at`` rows alongside the bearer string."""

    token: str
    jti: str
    expires_at: datetime


def _now() -> datetime:
    return datetime.now(tz=UTC)


def issue_access_token(
    *,
    user_id: int,
    role: str,
    secret: str,
    ttl_minutes: int,
    issued_at: datetime | None = None,
) -> str:
    """Issue a short-lived access token for ``user_id`` with ``role``."""
    now = issued_at or _now()
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    encoded: str = jwt.encode(claims, secret, algorithm=ALGORITHM)
    return encoded


def issue_refresh_token(
    *,
    user_id: int,
    secret: str,
    ttl_days: int,
    issued_at: datetime | None = None,
) -> IssuedRefreshToken:
    """Issue a refresh token. The returned ``jti`` should be persisted so the
    token can later be revoked or detected as missing during refresh."""
    now = issued_at or _now()
    expires_at = now + timedelta(days=ttl_days)
    jti = uuid.uuid4().hex
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    encoded: str = jwt.encode(claims, secret, algorithm=ALGORITHM)
    return IssuedRefreshToken(token=encoded, jti=jti, expires_at=expires_at)


def decode_token(token: str, *, secret: str, expected_type: TokenType) -> dict[str, Any]:
    """Decode and validate a JWT. Raises :class:`TokenError` on any failure.

    Failures collapsed: malformed token, bad signature, expired, or wrong
    ``type`` claim all surface as ``TokenError`` so callers don't have to
    distinguish between cases that are equivalent from a security standpoint.
    """
    try:
        claims: dict[str, Any] = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise TokenError(str(exc)) from exc

    actual_type = claims.get("type")
    if actual_type != expected_type:
        raise TokenError(f"expected token type {expected_type!r}, got {actual_type!r}")

    return claims

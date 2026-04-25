"""Unit tests for JWT issuance and decoding."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from shelvr.auth.tokens import (
    ALGORITHM,
    TokenError,
    decode_token,
    issue_access_token,
    issue_refresh_token,
)

SECRET = "unit-test-secret"


def test_issue_access_token_round_trip() -> None:
    token = issue_access_token(user_id=42, role="admin", secret=SECRET, ttl_minutes=15)
    claims = decode_token(token, secret=SECRET, expected_type="access")
    assert claims["sub"] == "42"
    assert claims["role"] == "admin"
    assert claims["type"] == "access"


def test_issue_refresh_token_round_trip_and_jti() -> None:
    issued = issue_refresh_token(user_id=7, secret=SECRET, ttl_days=30)
    claims = decode_token(issued.token, secret=SECRET, expected_type="refresh")
    assert claims["sub"] == "7"
    assert claims["jti"] == issued.jti
    assert claims["type"] == "refresh"
    assert issued.expires_at > datetime.now(tz=UTC)


def test_refresh_token_jti_is_unique_per_call() -> None:
    a = issue_refresh_token(user_id=1, secret=SECRET, ttl_days=1)
    b = issue_refresh_token(user_id=1, secret=SECRET, ttl_days=1)
    assert a.jti != b.jti


def test_decode_token_rejects_wrong_type() -> None:
    access = issue_access_token(user_id=1, role="reader", secret=SECRET, ttl_minutes=15)
    with pytest.raises(TokenError):
        decode_token(access, secret=SECRET, expected_type="refresh")


def test_decode_token_rejects_bad_signature() -> None:
    token = issue_access_token(user_id=1, role="reader", secret=SECRET, ttl_minutes=15)
    with pytest.raises(TokenError):
        decode_token(token, secret="different-secret", expected_type="access")


def test_decode_token_rejects_expired() -> None:
    past = datetime.now(tz=UTC) - timedelta(hours=1)
    token = issue_access_token(
        user_id=1, role="reader", secret=SECRET, ttl_minutes=15, issued_at=past - timedelta(hours=1)
    )
    with pytest.raises(TokenError):
        decode_token(token, secret=SECRET, expected_type="access")


def test_decode_token_rejects_malformed() -> None:
    with pytest.raises(TokenError):
        decode_token("not.a.jwt", secret=SECRET, expected_type="access")


def test_decode_token_rejects_unknown_algorithm() -> None:
    """A token signed with a different algorithm must not be accepted."""
    crafted = jwt.encode({"sub": "1", "type": "access"}, SECRET, algorithm="HS512")
    # Sanity check: our decoder uses HS256 only.
    assert ALGORITHM == "HS256"
    with pytest.raises(TokenError):
        decode_token(crafted, secret=SECRET, expected_type="access")

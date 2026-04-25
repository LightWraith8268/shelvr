"""Password hashing and verification using argon2id via passlib."""

from __future__ import annotations

from passlib.context import CryptContext

_password_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password using argon2id."""
    if not plaintext:
        raise ValueError("password must not be empty")
    hashed: str = _password_context.hash(plaintext)
    return hashed


def verify_password(plaintext: str, password_hash: str) -> bool:
    """Return True iff ``plaintext`` matches ``password_hash``.

    Returns False for any verification failure (wrong password, malformed hash,
    unsupported scheme) so callers don't have to distinguish — login flows
    treat all of those the same way.
    """
    try:
        result: bool = _password_context.verify(plaintext, password_hash)
    except (ValueError, TypeError):
        return False
    return result

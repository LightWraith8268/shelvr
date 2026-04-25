"""Unit tests for password hashing helpers."""

from __future__ import annotations

import pytest

from shelvr.auth.passwords import hash_password, verify_password


def test_hash_password_returns_argon2_hash() -> None:
    hashed = hash_password("hunter2")
    assert hashed.startswith("$argon2")
    assert hashed != "hunter2"


def test_verify_password_accepts_correct_password() -> None:
    hashed = hash_password("hunter2")
    assert verify_password("hunter2", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("hunter2")
    assert verify_password("wrong", hashed) is False


def test_verify_password_rejects_malformed_hash() -> None:
    assert verify_password("anything", "not-a-real-hash") is False


def test_hash_password_produces_unique_hashes_for_same_input() -> None:
    """Salting must make repeated hashes of the same password differ."""
    assert hash_password("hunter2") != hash_password("hunter2")


def test_hash_password_rejects_empty_string() -> None:
    with pytest.raises(ValueError):
        hash_password("")

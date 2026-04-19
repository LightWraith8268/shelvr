"""Tests for SHA-256 hashing helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path


def test_sha256_bytes_matches_stdlib() -> None:
    from shelvr.services.hashing import sha256_bytes

    data = b"hello world"
    expected = hashlib.sha256(data).hexdigest()
    assert sha256_bytes(data) == expected
    assert len(sha256_bytes(data)) == 64


def test_sha256_bytes_empty() -> None:
    from shelvr.services.hashing import sha256_bytes

    assert sha256_bytes(b"") == hashlib.sha256(b"").hexdigest()


def test_sha256_file_matches_bytes(tmp_path: Path) -> None:
    from shelvr.services.hashing import sha256_bytes, sha256_file

    data = b"the quick brown fox jumps over the lazy dog\n" * 100
    f = tmp_path / "input.bin"
    f.write_bytes(data)
    assert sha256_file(f) == sha256_bytes(data)


def test_sha256_file_streams_large_files(tmp_path: Path) -> None:
    """sha256_file handles files larger than the read-chunk."""
    from shelvr.services.hashing import sha256_file

    data = bytes(range(256)) * 8192  # 2 MiB
    f = tmp_path / "large.bin"
    f.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert sha256_file(f) == expected

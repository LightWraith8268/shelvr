"""SHA-256 hashing helpers for file and byte inputs."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 64 * 1024  # 64 KiB


def sha256_bytes(data: bytes) -> str:
    """Return the hex-encoded SHA-256 digest of a bytes object."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the hex-encoded SHA-256 digest of a file's contents.

    Streams in 64 KiB chunks so arbitrarily large files don't load into memory.
    """
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()

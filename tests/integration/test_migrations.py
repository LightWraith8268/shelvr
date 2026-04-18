"""Integration test: alembic upgrade head applies cleanly."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
def test_alembic_upgrade_head_applies_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running `alembic upgrade head` on an empty DB produces all tables."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("SHELVR_JWT_SECRET", "test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("SHELVR_DATABASE_URL", f"sqlite+aiosqlite:///{db_file.as_posix()}")

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"alembic failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert db_file.exists()

    # Verify a known table exists.
    import sqlite3

    conn = sqlite3.connect(db_file)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = {r[0] for r in rows}
        expected = {
            "alembic_version",
            "authors",
            "book_authors",
            "book_tags",
            "books",
            "devices",
            "formats",
            "identifiers",
            "jobs",
            "plugin_data",
            "reading_progress",
            "series",
            "tags",
            "users",
        }
        assert expected.issubset(table_names), f"missing: {expected - table_names}"
    finally:
        conn.close()

"""Integration tests for `shelvr user create`.

These tests are intentionally synchronous — the CLI's ``_run`` calls
``asyncio.run`` internally, which cannot be nested under pytest-asyncio's
event loop. Verifying the user row is done via a fresh sync engine.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from shelvr.auth.passwords import verify_password
from shelvr.cli import _run
from shelvr.db.base import create_engine
from shelvr.db.session import make_session_factory
from shelvr.repositories.users import UserRepository


def _migrate(database_url: str) -> None:
    """Apply alembic migrations against the given database URL."""
    from alembic.config import Config

    from alembic import command

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("+aiosqlite", ""))
    command.upgrade(config, "head")


def _set_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    db_path = tmp_path / "shelvr.db"
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("SHELVR_JWT_SECRET", "cli-test")
    monkeypatch.setenv("SHELVR_LIBRARY_PATH", str(tmp_path / "library"))
    monkeypatch.setenv("SHELVR_DATABASE_URL", database_url)
    return database_url


def _fetch_user(database_url: str, username: str):
    async def _go():
        engine = create_engine(database_url)
        try:
            async with make_session_factory(engine)() as session:
                return await UserRepository(session).get_by_username(username)
        finally:
            await engine.dispose()

    return asyncio.run(_go())


def test_create_user_creates_admin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = _set_env(monkeypatch, tmp_path)
    _migrate(database_url)

    exit_code = _run(["user", "create", "alice", "--admin", "--password", "hunter2"])
    assert exit_code == 0
    assert "created user 'alice'" in capsys.readouterr().out

    user = _fetch_user(database_url, "alice")
    assert user is not None
    assert user.role == "admin"
    assert user.is_active is True
    assert verify_password("hunter2", user.password_hash) is True


def test_create_user_default_role_is_reader(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database_url = _set_env(monkeypatch, tmp_path)
    _migrate(database_url)

    assert _run(["user", "create", "bob", "--password", "pw"]) == 0
    user = _fetch_user(database_url, "bob")
    assert user is not None
    assert user.role == "reader"


def test_create_user_rejects_duplicate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = _set_env(monkeypatch, tmp_path)
    _migrate(database_url)

    assert _run(["user", "create", "alice", "--password", "pw"]) == 0
    capsys.readouterr()  # discard

    assert _run(["user", "create", "alice", "--password", "pw"]) == 2
    assert "already exists" in capsys.readouterr().err


def test_create_user_rejects_empty_password(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _set_env(monkeypatch, tmp_path)
    assert _run(["user", "create", "alice", "--password", ""]) == 2
    assert "password must not be empty" in capsys.readouterr().err

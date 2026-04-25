"""`shelvr` console-script entry point.

Subcommands:
    shelvr serve                       Start the API server (default).
    shelvr user create <username>      Create a user account.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from collections.abc import Sequence

import uvicorn

from shelvr.auth.passwords import hash_password
from shelvr.config import load_settings
from shelvr.db.base import create_engine
from shelvr.db.session import make_session_factory
from shelvr.repositories.users import UserRepository


def _serve() -> None:
    """Start the Shelvr API server."""
    settings = load_settings()
    uvicorn.run(
        "shelvr.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


async def _create_user_async(*, username: str, password: str, role: str) -> int:
    settings = load_settings()
    engine = create_engine(settings.database_url)
    factory = make_session_factory(engine)
    try:
        async with factory() as session:
            repo = UserRepository(session)
            existing = await repo.get_by_username(username)
            if existing is not None:
                print(f"error: user {username!r} already exists", file=sys.stderr)
                return 2
            user = await repo.create(
                username=username, password_hash=hash_password(password), role=role
            )
            await session.commit()
            print(f"created user {user.username!r} (id={user.id}, role={user.role})")
            return 0
    finally:
        await engine.dispose()


def _create_user(args: argparse.Namespace) -> int:
    username: str = args.username
    role = "admin" if args.admin else "reader"

    password: str | None = args.password
    if password is None:
        password = getpass.getpass("Password: ")
        confirmation = getpass.getpass("Confirm: ")
        if password != confirmation:
            print("error: passwords do not match", file=sys.stderr)
            return 2
    if not password:
        print("error: password must not be empty", file=sys.stderr)
        return 2

    return asyncio.run(_create_user_async(username=username, password=password, role=role))


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser for the ``shelvr`` CLI."""
    parser = argparse.ArgumentParser(prog="shelvr", description="Shelvr server CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="Start the API server (default)")

    user_parser = subparsers.add_parser("user", help="User management")
    user_subparsers = user_parser.add_subparsers(dest="user_command", required=True)

    create_parser = user_subparsers.add_parser("create", help="Create a user account")
    create_parser.add_argument("username")
    create_parser.add_argument(
        "--admin", action="store_true", help="Create the user with role=admin (default reader)"
    )
    create_parser.add_argument(
        "--password",
        default=None,
        help="Password (omit to be prompted; required for non-interactive use)",
    )
    return parser


def _run(argv: Sequence[str] | None = None) -> int:
    """Dispatch the requested subcommand and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "serve"):
        _serve()
        return 0
    if args.command == "user" and args.user_command == "create":
        return _create_user(args)

    parser.print_help()
    return 2


def main(argv: Sequence[str] | None = None) -> None:
    """Console-script entry point. Exits the process with a status code."""
    sys.exit(_run(argv))


if __name__ == "__main__":
    main()

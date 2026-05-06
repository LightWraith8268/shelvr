"""PyInstaller entry point for the shelvrd Windows binary.

Resolves the bundle's _MEIPASS directory at startup so alembic finds its
script_location and uvicorn serves the SPA from web/dist when running from
the frozen executable, then delegates to the regular ``shelvr`` CLI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bundle_root() -> Path:
    """Return the directory that holds bundled data files at runtime."""
    if getattr(sys, "frozen", False):
        # PyInstaller sets ``_MEIPASS`` to the temp extraction root for
        # one-folder builds; fall back to the executable's directory.
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _prepare_environment() -> None:
    """Point alembic at the bundled migrations directory."""
    bundle = _bundle_root()
    alembic_ini = bundle / "alembic.ini"
    if alembic_ini.is_file():
        os.environ.setdefault("ALEMBIC_CONFIG", str(alembic_ini))
    # Ensure relative imports inside the frozen app resolve against the bundle.
    if str(bundle) not in sys.path:
        sys.path.insert(0, str(bundle))


def main() -> None:
    _prepare_environment()
    from shelvr.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()

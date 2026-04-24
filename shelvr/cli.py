"""`shelvr` console-script entry point.

Runs uvicorn against the FastAPI app with settings-driven host/port.
"""

from __future__ import annotations

import uvicorn

from shelvr.config import load_settings


def main() -> None:
    """Start the Shelvr API server."""
    settings = load_settings()
    uvicorn.run(
        "shelvr.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()

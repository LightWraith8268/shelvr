"""FastAPI app factory for Shelvr."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response

from shelvr import __version__
from shelvr.api.v1.router import router as v1_router
from shelvr.config import load_settings
from shelvr.db.base import create_engine
from shelvr.db.session import make_session_factory
from shelvr.logging_config import (
    bind_request_id,
    clear_request_context,
    configure_logging,
)


def create_app() -> FastAPI:
    """Build the FastAPI application.

    Side effects:
        - Loads settings (fails loudly if jwt_secret missing or library_path unset)
        - Configures structured logging
        - Creates the async SQLAlchemy engine + session factory
        - Stashes settings/engine/session_factory on app.state so routes can
          reach them via the helpers in shelvr.api.deps
        - Registers the v1 router and request-ID middleware
    """
    settings = load_settings()
    configure_logging(level=settings.log_level)

    app = FastAPI(
        title="Shelvr",
        version=__version__,
        description="Self-hosted ebook library server",
    )

    # Database engine + session factory live on app.state so routes can access
    # them via the dependency helpers in shelvr.api.deps.
    engine = create_engine(settings.database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)

    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        bind_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            clear_request_context()
        response.headers["X-Request-ID"] = request_id
        return response

    app.include_router(v1_router)
    return app

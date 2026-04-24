"""Structured logging setup using structlog.

Every log line carries a request_id, plus user_id/plugin_id when bound.
"""

from __future__ import annotations

import logging
import uuid

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog + stdlib logging to emit JSON-ish structured lines."""
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_request_id(request_id: str | None = None) -> str:
    """Bind a request_id to the current context. Generate one if not provided."""
    rid = request_id or uuid.uuid4().hex[:12]
    bind_contextvars(request_id=rid)
    return rid


def clear_request_context() -> None:
    """Clear all structlog context vars. Call at request end."""
    clear_contextvars()

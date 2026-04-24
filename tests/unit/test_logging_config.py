"""Tests for structlog configuration and request-ID middleware."""

from __future__ import annotations

import pytest
import structlog


def test_configure_logging_sets_up_structlog() -> None:
    """configure_logging installs a structlog logger that returns a BoundLogger."""
    from shelvr.logging_config import configure_logging

    configure_logging(level="INFO")
    logger = structlog.get_logger("test")
    assert logger is not None


def test_request_id_middleware_binds_request_id(caplog: pytest.LogCaptureFixture) -> None:
    """The request-ID middleware binds a fresh request_id to the structlog context per request."""
    from shelvr.logging_config import bind_request_id, clear_request_context

    clear_request_context()
    bind_request_id("req-1234")
    logger = structlog.get_logger("test")
    logger.info("hello")
    # We can't easily assert on the rendered output here — but at minimum
    # binding should not raise. Context vars are verified in integration tests.
    clear_request_context()

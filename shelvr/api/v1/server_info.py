"""GET /api/v1/server/info — health and feature-discovery endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from shelvr import __version__

PROTOCOL_VERSION = 1
FEATURES = ["opds", "plugins", "jwt_auth"]


class ServerInfo(BaseModel):
    """Response shape for /server/info."""

    version: str
    protocol_version: int
    features: list[str]


router = APIRouter(prefix="/server", tags=["server"])


@router.get("/info", response_model=ServerInfo)
async def server_info() -> ServerInfo:
    """Return server version, protocol version, and enabled feature flags."""
    return ServerInfo(
        version=__version__,
        protocol_version=PROTOCOL_VERSION,
        features=FEATURES,
    )

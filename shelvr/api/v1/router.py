"""Aggregates all v1 sub-routers into a single APIRouter."""

from __future__ import annotations

from fastapi import APIRouter

from shelvr.api.v1 import auth, books, formats, server_info

router = APIRouter(prefix="/api/v1")
router.include_router(server_info.router)
router.include_router(auth.router)
router.include_router(books.router)
router.include_router(formats.router)

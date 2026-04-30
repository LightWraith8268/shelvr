"""Pydantic schemas for bookmark endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookmarkRead(BaseModel):
    """Public-safe bookmark shape."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    locator: str
    label: str | None
    created_at: datetime


class BookmarkCreate(BaseModel):
    """Body for POST /api/v1/books/{id}/bookmarks."""

    locator: str = Field(..., min_length=1, max_length=2000)
    label: str | None = Field(default=None, max_length=200)

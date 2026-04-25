"""Pydantic schemas for reading progress endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReadingProgressRead(BaseModel):
    """Public-safe progress shape."""

    model_config = ConfigDict(from_attributes=True)

    book_id: int
    locator: str
    percent: float
    updated_at: datetime


class ReadingProgressUpsert(BaseModel):
    """Body for PUT /api/v1/books/{id}/progress."""

    locator: str = Field(..., min_length=1, max_length=2000)
    percent: float = Field(..., ge=0.0, le=1.0)

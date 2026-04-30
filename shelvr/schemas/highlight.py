"""Pydantic schemas for highlight endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

HighlightColor = Literal["yellow", "green", "blue", "pink"]


class HighlightRead(BaseModel):
    """Public-safe highlight shape."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    locator_range: str
    text: str
    color: HighlightColor
    note: str | None
    created_at: datetime
    updated_at: datetime


class HighlightCreate(BaseModel):
    """Body for POST /api/v1/books/{id}/highlights."""

    locator_range: str = Field(..., min_length=1, max_length=4000)
    text: str = Field(default="", max_length=4000)
    color: HighlightColor = "yellow"
    note: str | None = Field(default=None, max_length=4000)


class HighlightUpdate(BaseModel):
    """Body for PATCH /api/v1/books/{id}/highlights/{hid}.

    All fields optional; ``note`` may be set to null to clear an existing note.
    """

    color: HighlightColor | None = None
    note: str | None = Field(default=None, max_length=4000)
    clear_note: bool = False

"""Readium-style Locator schema for cross-reader reading-position sync.

Subset of the Readium Web Publication Manifest "Locator" object
(https://readium.org/architecture/models/locators/). Used by readers like
KOReader and Thorium to roam between devices. Shelvr maps a single
``reading_progress`` row to a Locator and back, ignoring fields it doesn't
populate (``href``, ``type``, ``title``).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LocatorLocations(BaseModel):
    """Locations sub-object — at minimum carries progression and a fragment."""

    model_config = ConfigDict(extra="allow")

    progression: float | None = Field(default=None, ge=0.0, le=1.0)
    total_progression: float | None = Field(default=None, ge=0.0, le=1.0, alias="totalProgression")
    position: int | None = Field(default=None, ge=1)
    fragment: list[str] = Field(default_factory=list)


class Locator(BaseModel):
    """Readium Locator. Shelvr always emits ``locations.fragment[0]`` and
    ``locations.totalProgression`` for the current book. ``href``, ``type``,
    and ``title`` are pass-through optional metadata."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    href: str | None = None
    type: str | None = None
    title: str | None = None
    locations: LocatorLocations
    modified: datetime | None = None

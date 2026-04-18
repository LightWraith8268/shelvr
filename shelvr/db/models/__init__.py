"""SQLAlchemy model re-exports."""

from __future__ import annotations

from shelvr.db.models.author import Author
from shelvr.db.models.series import Series

__all__ = ["Author", "Series"]

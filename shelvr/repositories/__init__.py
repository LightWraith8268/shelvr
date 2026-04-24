"""Repositories -- the sole DB-access surface for services and routes."""

from __future__ import annotations

from shelvr.repositories.books import BookRepository

__all__ = ["BookRepository"]

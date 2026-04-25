# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-04-25

- Merge pull request #6 from LightWraith8268/claude/dev
- feat(auth): self-service password change with refresh-token revocation

## [0.3.0] - 2026-04-25

- Merge pull request #5 from LightWraith8268/claude/dev
- feat(plugins): admin enable/disable endpoints with persisted state

## [0.2.1] - 2026-04-25

- Merge pull request #4 from LightWraith8268/claude/dev
- fix(ci): explicitly dispatch release after auto-merge
- Merge pull request #3 from LightWraith8268/claude/dev
- chore(ci): use annotated tags in release workflow and rewrite v0.2.0 changelog

## [0.2.0] - 2026-04-25

First tagged release. Cumulative shipping of Days 1-13 of the build plan.

### Added

- **Server foundation:** FastAPI app factory, async SQLAlchemy 2.0 + aiosqlite + Alembic, pydantic-settings loader (defaults → `shelvr.toml` → `SHELVR_*` env), structlog with request-ID binding, `127.0.0.1` default bind.
- **Plugin system from day 1:** PluginRegistry with priority-ordered hook dispatch and error isolation, filesystem PluginLoader, manifest validation, `PluginContext`/`Plugin` base class, built-in EPUB / PDF / MOBI plugins, `hello_world` reference plugin.
- **Import pipeline:** SHA-256 dedupe-on-upload, filesystem rollback on DB failure, tag/author dedup case-insensitive, Pillow cover thumbnails (small/medium).
- **Books API:** `POST /api/v1/books` (multipart upload, admin), `GET /api/v1/books` with pagination, sort, search, and tag/author/language filters; `GET /{id}`, `/cover`, `PATCH /{id}` (admin) for partial metadata edits, `DELETE /{id}` (admin) with on-disk file cleanup.
- **Format download:** `GET /api/v1/formats/{id}/file` streams the underlying ebook with the right MIME (epub, pdf, mobi, azw3).
- **Facets:** `GET /api/v1/{tags,authors,languages}` for UI filter panels with usage counts.
- **JWT auth:** `/api/v1/auth/{login,refresh,logout,me}` with refresh-token rotation; refresh tokens DB-backed and revocable. HTTP Basic accepted alongside Bearer so OPDS readers (KOReader, Moon+ Reader, Aldiko) work without bespoke OAuth.
- **OPDS 1.2 catalog** at `/api/v1/opds`: root navigation feed plus paginated acquisition feeds for `/all`, `/by-tag/{name}`, and `/by-author/{id}`.
- **Web UI** under `web/` (Vite + React 19 + TS + Tailwind + TanStack Query + react-router-dom): login, library grid with tag/author/language filters, book detail with cover and per-format download, admin upload page (drag-drop), admin metadata edit, admin delete, header username/role/sign-out. `web/dist/` committed so server install needs no Node.
- **CLI:** `shelvr serve` (default) and `shelvr user create <username> [--admin] [--password ...]` for bootstrap account creation.

## [Unreleased]

# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- JWT authentication: `/api/v1/auth/{login,refresh,logout,me}` with refresh-token rotation; HTTP Basic auth accepted alongside Bearer so OPDS readers (KOReader, Moon+ Reader, Aldiko) can connect.
- React + Vite + TypeScript + Tailwind web UI under `web/`: login, library grid with tag/author/language filters, book detail with cover and per-format download, admin upload page (drag-drop), admin metadata edit, admin delete.
- OPDS 1.2 catalog at `/api/v1/opds`: root navigation feed plus paginated acquisition feeds for all books, by-tag, and by-author.
- Book API: `GET /api/v1/books` with pagination, sort, search, and tag/author/language filters; `GET /{id}`, `/cover`, `PATCH /{id}` (admin), `DELETE /{id}` (admin); `POST /` multipart upload (admin).
- Format download: `GET /api/v1/formats/{id}/file` streams the underlying ebook with the right MIME type (epub, pdf, mobi, azw3).
- Facet endpoints: `GET /api/v1/{tags,authors,languages}` for UI filters.
- Plugin system from day 1: built-in EPUB / PDF / MOBI plugins, hello_world reference, hook-dispatch with priority ordering and error isolation, plugin discovery into `app.state.plugins`.
- CLI: `shelvr serve` (default) and `shelvr user create <username> [--admin] [--password ...]` for bootstrap account creation.
- Importer: dedupe-on-upload via SHA-256 file hash, filesystem rollback on DB failure, tag/author dedup case-insensitive.

### Notes

- Pre-alpha. Schema and API surfaces may change without migration paths until v1.0.0.
- Server binds `127.0.0.1` by default; LAN exposure is opt-in.

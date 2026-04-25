# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-25

- Merge pull request #2 from LightWraith8268/claude/dev
- fix(ci): trigger auto-merge from CI workflow_run instead of brittle wait-on-check
- chore(format): apply ruff format
- chore(ci): auto-merge claude/dev to main and release pipeline
- feat(opds): browse-by-tag and browse-by-author navigation feeds
- feat(books): tag/author/language filters and facet endpoints
- feat(books): admin edit and delete endpoints with web UI
- feat(opds): OPDS 1.2 catalog at /api/v1/opds with HTTP Basic auth
- feat(web): admin upload UI with drag-drop and per-file status
- feat(web): login flow, auth-aware API client, and authed media loading
- feat(cli): shelvr user create subcommand for bootstrap account creation
- feat(auth): gate book and format routes with bearer auth
- feat(auth): /auth/login, /auth/refresh, /auth/logout endpoints
- feat(auth): JWT access and refresh token issuance and decoding
- feat(auth): user auth fields, refresh tokens table, and password hashing
- feat(web): mount built SPA with client-side router fallback
- feat(web): book detail page with react-router
- feat(web): library grid view with search, sort, and pagination
- feat(web): scaffold React + Vite + TS + Tailwind frontend
- feat(api): book detail, cover, and format download endpoints
- feat(api): add GET /api/v1/books list endpoint
- fix(import): dedupe tags/authors and roll back files on DB failure
- Merge pull request #1 from LightWraith8268/claude/dev
- Merge remote-tracking branch 'origin/main' into claude/dev
- Create README.md
- refactor(import): dispatch via on_format_import plugin hook; remove legacy readers
- feat(plugins): add MOBI built-in plugin
- feat(plugins): add PDF built-in plugin
- feat(plugins): add EPUB built-in plugin
- feat(plugins): allow dot-separated namespace IDs (e.g. builtin.epub)
- feat(plugins): wire built-in plugin discovery into create_app
- feat(plugins): add handler-hook dispatch with priority ordering and FormatImportResult
- feat(plugins): wire PluginRegistry into app.state and fire on_book_added from importer
- feat(plugins): add hello_world reference plugin
- feat(plugins): add PluginRegistry with event dispatch and error isolation
- feat(plugins): add PluginLoader for filesystem discovery and instantiation
- feat(plugins): add manifest parser with Pydantic schema and api_version check
- feat(plugins): add PluginContext and Plugin base class
- feat(plugins): add plugin exception hierarchy
- feat(import): add import pipeline with POST /api/v1/books endpoint
- feat(repositories): add BookRepository with create_from_metadata + dedup helpers
- feat(services): add covers service with Pillow thumbnail generation
- feat(services): add hashing and file-layout helpers for import pipeline
- feat(schemas): add Pydantic book schemas (Create/Update/Read + nested types)
- chore(deps): add Pillow and python-multipart for import pipeline
- feat(formats): add reader registry with extension-based dispatch
- feat(formats): add MOBI reader using mobi package and OPF parsing
- feat(formats): add PDF reader using pymupdf
- feat(formats): add EPUB reader using ebooklib
- feat(formats): add Metadata model and FormatReadError hierarchy
- test(fixtures): add small public-domain ebook fixtures (PG #1080)
- chore(deps): add ebooklib, pymupdf, and mobi for format readers
- chore(lint): exclude alembic/versions from ruff
- feat(cli): add shelvr console-script entry point
- feat(api): add FastAPI app factory, v1 router, and /api/v1/server/info endpoint
- feat(logging): add structlog configuration with request-ID binding
- feat(db): add initial Alembic migration for all v1 tables
- feat(db): initialize async Alembic environment
- feat(db): add PluginData model with composite unique (plugin_id, key)
- feat(db): add Job model
- feat(db): add User, Device, and ReadingProgress models
- feat(db): add Identifier model with composite unique (book_id, scheme, value)
- feat(db): add Format model with globally unique file_hash
- feat(db): add Book model with author and tag relationships
- feat(db): add Tag model with unique name
- feat(db): add Series model
- feat(db): add Author model
- feat(db): add async session factory and get_session generator
- feat(db): add declarative Base with naming convention and async engine factory
- test: add shared pytest fixtures for settings, engine, and session
- refactor(config): strengthen env-over-toml test and tighten TomlSource types
- docs: add annotated shelvr.toml.example
- feat(config): add pydantic-settings loader with TOML + env override precedence
- chore: scaffold empty Python package layout
- docs: move kickoff prompt to docs/ and convert strategy doc to Markdown
- ci: add lint, type-check, and test workflow
- docs: add README and AGPL-3.0 LICENSE
- chore: add pyproject.toml with dependencies and tool configuration
- chore: initialize git repository with .gitignore and .gitattributes

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

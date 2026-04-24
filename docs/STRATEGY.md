# Shelvr Strategy & Architecture

Architecture & Roadmap

Self-hosted ebook library server with Android companion — an Ink & Iron Apps product

0. Name and Identity

Product name: Shelvr. A shelf is where books live, and shelving is what the app does — take a scattered collection of ebook files and organize them into a browsable library. Joins the Ink & Iron Apps product line (Simmer, Anvil, LibraryIQ, YardIQ, FlowFic, MatCalc) as the seventh product, sharing the short-single-word naming pattern used by Simmer and Anvil.

Publisher: Ink & Iron Apps — inknironapps.com. Product pages and documentation live under the brand site, which carries the SEO and discoverability work. The product name does not need to dominate search on its own.

Server: Shelvr (runs as a Windows service named shelvrd).

Android app: Shelvr — same name, same brand, like Plex's server and client both being 'Plex'.

Conventions: config at shelvr.toml, data dir at %APPDATA%/Shelvr/, API under /api/v1/, plugins discovered under plugins/. GitHub repos under the Ink & Iron org (e.g. inkandiron/shelvr-server, inkandiron/shelvr-android).

Relationship to LibraryIQ: LibraryIQ and Shelvr are intentional companions in the Ink & Iron lineup. LibraryIQ is an Android app for cataloging a user's physical book collection, backed by Firebase with cross-device sync and paywalled AI features. Shelvr is a self-hosted server for managing the user's digital collection. Together they cover the full shelf. Detailed strategy for how the two products interact and differ is in Section 0.1 below.

0.1. Product Strategy: Shelvr alongside LibraryIQ

Shelvr and LibraryIQ share a brand and a thematic mission (manage the user's library, physical and digital), but they should remain architecturally separate products. The decision not to merge them is deliberate and worth documenting.

Why they stay separate

The architectures are fundamentally incompatible in ways that matter to users:

LibraryIQ is cloud-first. Firebase backend, sync-as-a-service, paywalled premium features including AI. The value proposition is polish and convenience in exchange for a subscription.

Shelvr is self-hosted-first. User's own Windows hardware, local network, no cloud dependencies. The value proposition is ownership and privacy — the opposite of LibraryIQ's posture.

These attract different user mindsets. Merging would force compromise on both fronts: Shelvr with a Firebase dependency loses the self-hosted audience entirely; LibraryIQ with a self-hosted option loses the subscription model and absorbs enormous support burden. Kept separate, they complement rather than compete.

Portfolio-wise this is also an advantage: LibraryIQ is Ink & Iron's recurring-revenue product; Shelvr is the community-facing one-time-purchase product. Different customer acquisition, different LTV, different risk profile.

Integration levels (for future versions)

Instead of merging, build a thin bridge between the apps. From lightest to heaviest:

Level 1 — shared identifiers only: LibraryIQ gets a 'digital copy' field on each physical book that stores a Shelvr book ID or resolvable ISBN. Tapping it deep-links into Shelvr if installed. Shelvr has the same in reverse. No server-to-server traffic — the Android device is the bridge. Low cost, high payoff.

Level 2 — read-only API bridge: LibraryIQ consumes Shelvr's REST API directly to show 'you also own this digitally' badges. Requires LibraryIQ to know a Shelvr server URL (user-pasted or mDNS-discovered).

Level 3 — LibraryIQ stores Shelvr connection info: Encrypted Shelvr server credentials sync through LibraryIQ's Firebase profile so the integration works across all the user's devices. Overkill unless there's clear demand.

Recommendation: target Level 1 for LibraryIQ v-next and Shelvr v2. It delivers the 'unified shelf' pitch without architectural entanglement. Upgrade only if users ask. Shelvr's identifiers table should include a 'libraryiq' scheme from v1 so no schema migration is needed later.

Shelvr posture on paywalls and AI

LibraryIQ monetizes via subscriptions and paywalled AI. Shelvr should take the opposite posture, at least for v1 and v2:

Windows server: free and open source — no paywalls, no cloud dependencies, no telemetry-by-default.

Android companion app: closed source, $0.99 one-time purchase via Google Play.

Any future AI features ship as optional plugins that phone home to an Ink & Iron backend. Core stays clean. Users who already subscribe to LibraryIQ premium get the Shelvr AI plugin included — this is how the two products reinforce each other without entangling their codebases.

The self-hosted audience is allergic to surprise paywalls or unexpected cloud dependencies. Shipping Shelvr clean and adding optional premium plugins later is additive and acceptable. Shipping any cloud requirement or paywall gate on core functionality would permanently damage the product's standing with its target users.

Pricing model for Shelvr

Windows server: Free. Open source. Licensed AGPL-3.0 (see rationale below). Distributed via GitHub releases and a signed Windows installer from inknironapps.com.

Android client: $0.99 one-time purchase on Google Play. Closed source. Polished, first-party, with offline reading, mDNS discovery, and native Readium integration.

Future premium plugins: priced individually or bundled into an Ink & Iron Premium subscription if multiple products across the portfolio have AI features. This is a decision for later — not v1 or v2.

Why this split works: the server lives on hardware the user already paid for and needs to be auditable and trustworthy, so it's open and free. The client competes on UX quality with consumer apps in the $3–10 range, so 99¢ is a trivial ask that filters out spam installs while signaling it's a real product. Open server + paid closed client is a proven pattern (Plex's model is similar, though with a different pricing structure).

License choice: AGPL-3.0 for the server

For a solo-dev open source server with a paid closed companion, AGPL-3.0 is the right license:

Protects against commercial repackaging — anyone who forks Shelvr and offers it as a hosted service must also open-source their modifications. Prevents a cloud vendor from cloning the work without contributing back.

Does not restrict the paid Android client. AGPL applies to the server code; a separate client communicating over a network is a separate work and can be closed source and paid.

Aligns with Calibre's GPLv3 license, which matters for the v2 conversion plugin that will likely shell out to ebook-convert.

Matches what comparable projects use (Grafana, Jellyfin, Mastodon) so it sends the right signal to the self-hosted community.

1. Overview

Shelvr is a self-hosted ebook library with a Windows server and Android companion app, inspired by Plex's server/client model. The Windows machine holds the canonical library, metadata database, and does the heavy lifting. Android is a thin client that browses, streams, downloads-for-offline, and reads.

The defining architectural feature is a first-class plugin system that exposes hooks at every meaningful point in the book lifecycle — import, metadata extraction, conversion, export, UI extension, and scheduled jobs. Core stays small; capabilities grow through plugins.

Design Principles

Thin client, fat server. Android does UI; Windows does everything else.

Plugin-first. Every non-trivial feature should be implementable as a plugin.

Local-first. Works fully on your LAN with no internet. Cloud features are optional plugins.

Schema stability. The data model is designed for v3 from day one, even if v1 only exercises part of it.

Fail loud on format boundaries. Reject unsupported formats with clear errors; don't silently lose data.

2. Technology Stack

Server (Windows)

Layer

Choice

Why

Language

Python 3.11+

Best ebook library ecosystem; plugin-friendly; matches Calibre's world

Web framework

FastAPI

Async, auto-generated OpenAPI, excellent typing, lightweight

Database

SQLite + SQLAlchemy

Zero-config, single file, plenty for one user; SQLAlchemy eases future Postgres migration

Job queue

APScheduler (v1) → RQ/Redis (v2+)

In-process is fine until conversion lands

Packaging

PyInstaller + NSIS installer

Single .exe + Windows service via nssm or native service wrapper

Auth

JWT with refresh tokens

Works identically for web and Android

Android Client

Layer

Choice

Why

Language

Kotlin

Modern standard for Android

UI

Jetpack Compose

Faster iteration than XML layouts; good for a catalog-style UI

Networking

Retrofit + OkHttp

Standard, well-understood, handles auth interceptors cleanly

Local storage

Room (SQLite)

Offline catalog cache + downloaded book index

Reader

Readium Kotlin Toolkit

Production-quality EPUB reader; saves months of work

Image loading

Coil

Compose-native, handles cover thumbnails well

Web UI (for server admin)

A lightweight React + Vite SPA served by FastAPI. Not a separate deployment — just static files. This is where you manage the library from the Windows machine itself: import books, edit metadata in bulk, configure plugins, view logs.

3. Data Model

Designed now to support v3 without schema migrations beyond adding columns. The key insight: a Book is an abstract work; Formats are concrete files. One book, many formats — this matters the moment conversion exists.

Core tables

books

  id                INTEGER PRIMARY KEY

  title             TEXT NOT NULL

  sort_title        TEXT         -- 'Great Gatsby, The'

  series_id         INTEGER FK -> series.id NULL

  series_index      REAL NULL    -- 1.0, 1.5, 2.0

  description       TEXT

  language          TEXT         -- ISO 639-1

  publisher         TEXT

  published_date    DATE

  isbn              TEXT

  rating            INTEGER      -- 0-10

  date_added        TIMESTAMP

  date_modified     TIMESTAMP

  cover_path        TEXT         -- relative to library root

 

authors

  id, name, sort_name

 

book_authors       (book_id, author_id, role)   -- role: author/editor/translator

 

series

  id, name, sort_name, description

 

tags

  id, name, color

 

book_tags          (book_id, tag_id)

 

formats

  id                INTEGER PRIMARY KEY

  book_id           INTEGER FK -> books.id

  format            TEXT         -- 'epub', 'pdf', 'mobi'

  file_path         TEXT         -- relative to library root

  file_size         INTEGER

  file_hash         TEXT         -- SHA-256, for dedup

  date_added        TIMESTAMP

  source            TEXT         -- 'import', 'conversion', 'plugin:x'

 

identifiers

  book_id, scheme, value           -- ('isbn','...'), ('goodreads','...'), ('asin','...')

 

reading_progress

  book_id, device_id, locator, percent, updated_at

  -- locator is a Readium-compatible JSON blob: CFI or page+offset

 

plugin_data

  plugin_id, key, value_json      -- KV store scoped per-plugin

 

jobs

  id, type, status, payload_json, result_json, created_at, updated_at

  -- type: 'import', 'convert', 'metadata_fetch', 'plugin:xyz'

 

users

  id, username, password_hash, role        -- 'admin' or 'reader'

 

devices

  id, user_id, name, platform, last_seen, push_token

Why this shape: books is the stable identity. formats lets v2 store an EPUB and a converted MOBI of the same book with independent hashes. reading_progress is per-device so Windows web reader and Android don't clobber each other (with sync logic on top). plugin_data gives plugins a place to persist without schema changes.

4. Plugin System

This is the load-bearing architectural decision. Get this right in v1 and everything else is additive.

Plugin structure

plugins/

  my_plugin/

    plugin.toml          # manifest: id, version, hooks, config schema

    __init__.py          # class MyPlugin(Plugin): ...

    ui/                  # optional React components for web UI

    assets/              # icons, static files

Manifest (plugin.toml)

[plugin]

id = "goodreads_metadata"

name = "Goodreads Metadata Fetcher"

version = "1.0.0"

author = "you"

api_version = "1"             # which host API this targets

 

[hooks]

on_metadata_fetch = true

on_book_added = true

 

[config]

api_key = { type = "string", secret = true, required = true }

prefer_over_local = { type = "bool", default = false }

 

[permissions]

network = ["*.goodreads.com"]

filesystem = "read"          # read | write | none

Hook lifecycle (v1)

Hook

When it fires

What it can do

on_startup

Server boot

Register routes, schedule jobs, warm caches

on_shutdown

Server stop

Flush state, close connections

on_book_added

New book in library

Enrich metadata, trigger downstream work

on_book_updated

Metadata or file change

React to edits, re-index search

on_format_import

Format file added

Extract metadata from the file

on_metadata_extract

Host asks for metadata

Return structured metadata from a source

on_metadata_fetch

User clicks 'fetch metadata'

Query external service, return candidates

register_routes

Startup

Add HTTP endpoints under /plugins/<id>/

register_ui

Startup

Declare UI extension points (book detail panel, sidebar item, etc.)

register_jobs

Startup

Schedule recurring work (cron-like)

Plugin base class

class Plugin:

    id: str

    version: str

 

    def __init__(self, context: PluginContext):

        """context gives access to db, config, logger, http, storage"""

        self.ctx = context

 

    # lifecycle

    def on_startup(self): pass

    def on_shutdown(self): pass

 

    # book events (return None or modified dict)

    def on_book_added(self, book): pass

    def on_book_updated(self, book, changes): pass

    def on_format_import(self, format, file_path): pass

 

    # metadata

    def on_metadata_fetch(self, query) -> list[MetadataCandidate]: return []

    def on_metadata_extract(self, file_path, format) -> Metadata | None: return None

 

    # extension points

    def register_routes(self, router): pass

    def register_ui(self) -> list[UIExtension]: return []

    def register_jobs(self, scheduler): pass

PluginContext (what plugins get access to)

ctx.db: scoped SQLAlchemy session; plugins cannot touch core tables directly, only via provided repository methods

ctx.config: typed access to this plugin's config from the manifest schema

ctx.storage: plugin-scoped KV store (backed by plugin_data table) and file storage under plugins/<id>/data/

ctx.http: HTTP client pre-configured with timeout, retry, and the plugin's declared network allowlist

ctx.logger: namespaced logger that shows up in the admin UI

ctx.library: high-level library API — search books, get cover, add format, etc.

Isolation and safety

v1 runs plugins in-process. This is fast and simple but means a bad plugin can crash the server. Mitigations: every hook call is wrapped in try/except with logging; slow plugins get a timeout; a circuit breaker disables plugins that fail repeatedly. v2+ can optionally move plugins to subprocesses if needed — the API is designed to survive that change.

5. Server-Client Protocol

Shelvr uses a custom REST + JSON API as its primary protocol, with OPDS 1.2 offered alongside as a compatibility layer for third-party readers. This matches the pattern of every other Plex-like app (Plex, Jellyfin, Kavita, Komga) and is a deliberate rejection of using OPDS as the main channel.

Why not OPDS-primary

OPDS is a good standard for what it is — a catalog-browsing feed built on Atom/XML. But it was never designed to be the backbone of a rich client experience, and it's missing most of what Shelvr needs:

No reading-progress sync in the spec

No annotations or highlights sync

No real-time updates — feeds are pull-based; no websockets, no push

No metadata editing — OPDS is read-only by design

No job status for imports or conversions

No home for plugin-registered routes or UI extensions

Limited search (no faceted filters, tag combinations, or smart collections)

Authentication is awkward compared to JWT

Building the Android app on OPDS would mean bolting custom extensions onto an XML feed for every interactive feature, ending up with OPDS for catalog browsing plus a parallel custom API for everything else. Worse than just having one well-designed API.

The dual approach

Primary: REST + JSON under /api/v1/, JWT auth, websockets for live updates. The Android app, web admin UI, and any future desktop client all use this.

Secondary: OPDS 1.2 feed at /api/v1/opds, read-only, auth via HTTP Basic or token. Exists purely so KOReader, Librera, Moon+ Reader, and other third-party readers can connect. It's about a day of work on top of the REST API since it's just a different view of the same data.

Week-one payoff: shipping OPDS from v1 means you can point an existing Android OPDS reader at Shelvr on day 7, before writing a single line of Kotlin. That validates the data model and import pipeline without the native app being on the critical path.

Versioning

All REST endpoints live under /api/v1/. A protocol_version field is included in the /api/v1/server/info response. The Android app checks this on connect and can warn on mismatch. OPDS follows its own versioning.

Core REST endpoints (v1)

POST   /api/v1/auth/login           -> { access_token, refresh_token }

POST   /api/v1/auth/refresh

 

GET    /api/v1/server/info          -> { version, protocol_version, features }

 

GET    /api/v1/books                -> paginated, filterable, sortable list

GET    /api/v1/books/{id}           -> full book with all formats

PATCH  /api/v1/books/{id}           -> edit metadata

DELETE /api/v1/books/{id}

POST   /api/v1/books                -> import new book (multipart upload)

 

GET    /api/v1/books/{id}/cover     -> image (supports ?size=thumb|medium|full)

GET    /api/v1/books/{id}/formats/{fmt}/file   -> download the actual file

GET    /api/v1/books/{id}/formats/{fmt}/stream -> ranged streaming for reader

 

GET    /api/v1/search?q=...

 

GET    /api/v1/authors, /series, /tags

 

POST   /api/v1/books/{id}/progress  -> update reading progress

GET    /api/v1/books/{id}/progress

 

GET    /api/v1/jobs                 -> list jobs (for Android progress UI)

WS     /api/v1/events               -> websocket for live updates

 

GET    /api/v1/plugins              -> installed plugins

POST   /api/v1/plugins/{id}/enable

POST   /api/v1/plugins/{id}/disable

GET    /api/v1/plugins/{id}/config

PUT    /api/v1/plugins/{id}/config

*      /api/v1/plugins/{id}/* -> routes registered by the plugin itself

 

# Compatibility layer

GET    /api/v1/opds                 -> OPDS 1.2 root catalog

GET    /api/v1/opds/new, /authors, /series, /tags  -> OPDS subfeeds

Android-specific behaviors

Server discovery via mDNS/Bonjour on the LAN — Android finds the Windows server without typing an IP

'Download for offline' stores the format file + cover + metadata snapshot in app storage

Reading progress sync on app resume and when closing a book

Optimistic UI: metadata edits apply locally first, sync when reachable

Websocket subscription for live job updates (import progress, v2 conversion progress) — replaces polling

6. Import Pipeline (v1)

This is the critical user-facing flow. A file lands; what happens?

1. Receive file (upload, watch folder, or API)

2. Compute hash → check for duplicate format

3. Identify format by extension + magic bytes

4. Reject if format not in supported set (v1: epub, pdf, mobi/azw3)

5. Move file into library structure:

     library/Author Name/Book Title (year)/Book Title.epub

6. Fire on_format_import hooks → core extracts minimal metadata from the file itself

7. Create Book + Format records (or attach Format to existing Book if matched)

8. Fire on_book_added hooks → plugins enrich (cover, description, ISBN, etc.)

9. Generate cover thumbnails (small/medium) and cache

10. Index for full-text search (SQLite FTS5)

Matching an imported format to an existing book uses: exact ISBN, then (normalized title + primary author) with fuzzy match. Uncertain matches go to a review queue rather than auto-merging.

7. Roadmap

v1 — Foundation (target: 3–6 weeks)

Goal: a daily-driver library with a solid plugin system. No conversion, three formats.

v1 must-have

Windows server: FastAPI + SQLite, runs as a service (shelvrd)

Supported formats: EPUB, PDF, MOBI/AZW3 — read-only metadata + serve file

Import: drag-drop, watch folder, API upload

Metadata extraction for all three formats (ebooklib, pymupdf, mobi)

Cover extraction + thumbnail generation

SQLite FTS5 full-text search over title/author/description/tags

Web admin UI: library grid, book detail, metadata editor, bulk edit, plugin manager

Plugin system: discovery, manifest parsing, lifecycle, all hooks listed above

Two reference plugins shipped in-tree: 'Open Library metadata fetcher' and 'Filename parser'

Primary REST API with JWT auth

OPDS 1.2 feed as a compatibility layer (read-only) so third-party readers work out of the box

Android app: browse, search, read EPUBs (via Readium), PDFs (via system or PdfRenderer), progress sync, download for offline

mDNS server discovery

Backup/restore: export library.db + config to a zip

v1 explicitly not-yet

No format conversion

No send-to-Kindle / external device sync

No multi-user beyond admin/reader roles

No annotations/highlights sync (reading position only)

No DRM handling of any kind

No cloud sync between multiple servers

v2 — Conversion + depth (target: +4–8 weeks after v1)

Goal: add format conversion, annotations, and multi-user polish. Still only the three base formats.

v2 headline features

Conversion engine (EPUB ↔ MOBI, PDF → EPUB best-effort), implemented as a plugin that wraps Calibre's ebook-convert CLI. Core provides the job queue and UI; conversion logic lives in the plugin.

Real job queue (RQ + Redis, bundled on Windows via embedded Redis or Memurai)

Annotations and highlights: schema, sync API, Android UI in the reader

Send-to-device: send a format to a folder, email (for Kindle Personal Documents), or webhook

Smart collections: saved queries that act like dynamic shelves

Reading stats: time read per day, streaks, per-book progress history

Per-user libraries (optional): isolate one user's view while sharing the underlying files

Plugin marketplace UI — browse, install from URL or local .zip, auto-update check

WebSocket channel for live updates (job progress, new imports) replacing polling

v2 data model additions

annotations table (book_id, user_id, type, locator, text, color, created_at)

collections table + smart_collections table with query JSON

conversion_profiles table (named presets: 'for Kindle', 'for Kobo', etc.)

reading_sessions table (book_id, user_id, started_at, ended_at, pages/percent delta)

v3 — Format expansion + ecosystem (target: ongoing)

Goal: support the long tail of formats and lean into the plugin ecosystem.

v3 headline features

Additional formats: CBZ/CBR (comics), DJVU, FB2, TXT, DOCX, RTF, LIT, HTML/HTMZ — each as a format plugin implementing metadata extraction and optional conversion

Audiobooks: M4B and MP3 with chapters — different enough that this might be a separate 'media type' at the core level (book vs audiobook)

OPDS 2.0 with authentication flows

Plugin SDK: published Python package, type stubs, cookiecutter template, documented contract, semver guarantees

Optional sandboxed plugins: run untrusted plugins in a subprocess with capability-based permissions

Multi-server federation: one Android app can connect to several servers and see a unified library

Optional cloud relay for access outside the LAN without port-forwarding (like Plex relay)

Desktop reader app for Windows (probably Tauri + the Readium JS toolkit) so you don't need a browser

Migration tools: import an existing Calibre library including custom columns

v3 architectural upgrades

Optional Postgres backend for users with large libraries (>50k books)

Pluggable storage backends: local filesystem, SMB, S3-compatible (so the library can live on a NAS)

Event bus — hooks become published events that plugins subscribe to, enabling cross-plugin coordination

8. Risks and Open Questions

Risk

Mitigation

Plugin API churn breaks v1 plugins by v3

api_version in manifest; adapter layer for old versions; deprecate before removing

Calibre CLI licensing (GPLv3) for v2 conversion

Ship it as a user-installed dependency (not bundled); document install step. Alternative: write conversion plugin against pandoc + ebooklib only for simple cases.

Android Readium license terms

Readium Kotlin is BSD-3; safe for any use. Confirm before committing.

MOBI/AZW3 parsing edge cases

Stick to reading metadata only in v1. Full MOBI write support is hard — defer to Calibre CLI in v2.

Windows service packaging complexity

Use nssm to wrap the Python executable as a service; proven approach.

SQLite concurrency under plugin load

Use WAL mode; keep plugin DB access via scoped sessions with short transactions.

User imports 100GB library on day one

Incremental import with resumable jobs and a progress UI from v1.

9. Concrete First-Week Plan

To turn this into real code rather than a plan, here's what to build first:

Day 1: Project skeleton. FastAPI app, SQLAlchemy models for books/authors/formats, Alembic migration, /api/v1/server/info endpoint. Project name: shelvr.

Day 2: Format readers. Write three small modules (epub.py, pdf.py, mobi.py) that each expose read_metadata(path) -> Metadata and extract_cover(path) -> bytes. No plugin system yet — just get the format layer right.

Day 3: Import pipeline. File upload endpoint → hash → dedup check → format reader → database write → cover thumbnail.

Day 4: Plugin loader. Manifest parsing, discovery, lifecycle, one trivial reference plugin (a 'hello world' that logs on_book_added).

Day 5: Refactor format readers to use on_format_import hook. The core 'just happens' to ship three built-in plugins. This proves the plugin API is sufficient for real work.

Day 6: Minimal web UI — library grid with covers, book detail page. Ugly is fine.

Day 7: Auth + OPDS compatibility feed. Point an existing Android OPDS reader (Librera, KOReader) at Shelvr to validate the data model and API surface before committing to the native client.

Why this order: by end of week 1 you have a working library you can point an existing OPDS reader at. That's your floor — every subsequent week adds capability, but Shelvr is useful from day 7. The native Android app then gets built against the richer REST API in week 2+, not against OPDS.

10. Follow-Up Documents

This document is the strategy and architecture reference — deliberately scoped to decisions that are expensive to change later (product positioning, data model shape, plugin API surface, pricing, licensing, high-level roadmap). Implementation-level detail lives in focused follow-up documents written closer to when they're needed, so they stay accurate rather than aspirational.

Planned follow-up docs and when to write them

PLUGIN_API.md — detailed plugin contract: full hook signatures, PluginContext API surface, manifest schema reference, type stubs, lifecycle diagrams, example plugins walked through end-to-end. Write: alongside v1 day 4 (plugin loader). Update whenever a hook is added or changed.

SECURITY.md — threat model, auth flow details (JWT rotation, refresh, revocation), TLS setup for LAN vs exposed deployments, plugin permission model in depth, secrets handling, responsible disclosure process. Write: before v1 public release.

DEPLOYMENT.md — Windows installer specifics, service registration, first-run wizard flow, upgrade path between versions, database migration strategy, backup/restore procedures, support bundle generation. Write: when packaging the v1 installer, around week 4-6.

CONFIG.md — complete shelvr.toml reference with every setting, default value, and what it controls. Environment variable overrides. Per-plugin config schema conventions. Write: incrementally during v1; finalize before release.

android/ARCHITECTURE.md — Android app internals: package structure, Room schema for cached catalog and downloaded books, sync conflict resolution, reader state persistence, background download/sync management, navigation graph, dependency injection setup. Write: when starting Kotlin work in week 2+.

TESTING.md — test strategy across layers: unit tests for format readers, integration tests for import pipeline, plugin test harness with mock context, Android instrumentation tests, sample corpus of test books (including malformed files to exercise error paths). Write: incrementally; stub it during v1 day 1 so the habit sticks.

OBSERVABILITY.md — structured logging conventions, error surfacing to admin UI, performance budgets (search latency targets, import throughput, memory ceilings), metrics for the admin dashboard. Write: when performance questions first become concrete — probably late v1.

CONTRIBUTING.md — contribution model: are PRs accepted, coding standards, commit style, how to submit a plugin, code of conduct. Write: when the repo goes public. Decide early whether this is accepting-patches open source or source-available; the distinction matters to contributors.

TELEMETRY.md (or a section in SECURITY.md) — explicit stance on telemetry and phone-home behavior: what the server and client do and don't send, update check behavior, opt-in crash reporting if any. Shelvr's self-hosted audience will read this carefully; make it short, honest, and specific. Write: before v1 public release.

MIGRATION.md — importing from Calibre, Kavita, Komga, or a bare folder of files. Export to Calibre-compatible format. Ensuring users can leave Shelvr as easily as they can join it — this is a trust commitment to the self-hosted audience. Write: early v3 when format expansion makes Calibre compatibility more natural.

I18N.md — internationalization plan (UI string extraction, locale handling, RTL support, book metadata in non-Latin scripts, date/number formatting). v1 and v2 ship English-only; this doc captures what needs to be retrofittable without schema changes. Write: before any translation work begins.

ACCESSIBILITY.md — WCAG 2.1 AA targets for the web UI, Android accessibility (TalkBack support, content descriptions, color contrast, font scaling respect). Write: before v1 release; accessibility retrofits are much harder than baking it in.

Doc location and format

All follow-up docs live in the shelvr-server repository under /docs, with the exception of android/ARCHITECTURE.md which lives in the shelvr-android repo. Markdown format, kept in version control alongside the code they describe. The strategy doc itself (this document) gets a .md version committed to /docs/STRATEGY.md so it evolves with the codebase rather than drifting as a detached Word file.

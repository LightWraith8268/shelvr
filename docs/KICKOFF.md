# Shelvr — Claude Code Kickoff Prompt

> Paste this entire document into Claude Code as your first prompt, or save it in the repo as `docs/KICKOFF.md` and reference it.

---

## Your task

Help me scaffold **Shelvr**, a self-hosted ebook library server with an Android companion app. This is day 1 of a multi-week project. I want you to act as a thoughtful collaborator: ask clarifying questions when decisions are load-bearing, push back when you see problems, and don't over-engineer things I haven't asked for yet.

We are working on the **Windows server** first. The Android app comes later, in its own repo.

## Product context (read before writing code)

- **Shelvr** is a Plex-style self-hosted ebook server. Windows runs the canonical library; clients (Android app, third-party OPDS readers, a web admin UI) connect to it.
- Part of the **Ink & Iron Apps** product lineup. Companion product is LibraryIQ (Android, physical book catalog, Firebase-backed, paywalled).
- **Pricing model**: Windows server is free and open source (AGPL-3.0). Android client is closed source, $0.99 one-time on Google Play. No cloud dependencies in core. Any future AI features will ship as optional plugins.
- **Target audience**: self-hosted / homelab users. They are allergic to telemetry, surprise paywalls, and cloud dependencies. Respect that posture in every decision.

## Core architectural decisions (do not relitigate these)

1. **Stack**: Python 3.11+, FastAPI, SQLAlchemy, SQLite (WAL mode), Alembic migrations. APScheduler for v1 job scheduling.
2. **API**: REST + JSON under `/api/v1/` is primary. JWT auth with refresh tokens. OPDS 1.2 feed at `/api/v1/opds` is a compatibility layer, not the main channel.
3. **Plugin system is first-class.** Core format readers (EPUB, PDF, MOBI) will themselves be implemented as built-in plugins. This forces the plugin API to be real.
4. **Data model is designed for v3 from day 1.** One book, many formats. Plugin KV store from day 1. Identifiers table with a `scheme` field that will later support `libraryiq`, `isbn`, `goodreads`, etc.
5. **Supported formats in v1**: EPUB, PDF, MOBI/AZW3. Read-only metadata + serve file. No conversion in v1. Conversion comes in v2 as a plugin wrapping Calibre's `ebook-convert`.
6. **Project name and conventions**:
    - Repo: `shelvr-server` (under the `inkandiron` GitHub org)
    - Windows service: `shelvrd`
    - Config file: `shelvr.toml`
    - Data directory: `%APPDATA%/Shelvr/` on Windows, `~/.shelvr/` for dev
    - Python package name: `shelvr`

## Conventions I want you to follow

- **Type hints on everything.** Use `from __future__ import annotations` at the top of every module.
- **Pydantic v2** for API schemas. Distinguish `BookCreate`, `BookUpdate`, `BookRead` models — don't reuse one model for all three.
- **Repository pattern** for database access. API routes never touch SQLAlchemy sessions directly; they go through repositories.
- **Dependency injection** via FastAPI's `Depends()`. No global state.
- **Structured logging** with `structlog`. Every log line has context (request_id, user_id if applicable, plugin_id if applicable).
- **Async everywhere** on the API layer. Use `asyncio`-compatible libraries (`aiosqlite` via SQLAlchemy async, `httpx` not `requests`).
- **Tests colocated** in `tests/` mirroring the source tree. `pytest`, `pytest-asyncio`, `httpx.AsyncClient` for API tests.
- **No secrets in code.** Config via `shelvr.toml` plus environment variable overrides (`SHELVR_*` prefix).
- **Every public function has a docstring.** One-line summary minimum; longer when the behavior isn't obvious.

## Directory structure I want

```
shelvr-server/
├── pyproject.toml
├── README.md
├── LICENSE                        # AGPL-3.0
├── .gitignore
├── .github/
│   └── workflows/ci.yml           # lint + test on PR
├── alembic.ini
├── alembic/
│   └── versions/
├── docs/
│   ├── STRATEGY.md                # (I'll paste strategy doc content here)
│   ├── PLUGIN_API.md              # write alongside plugin loader
│   └── TESTING.md                 # stub on day 1
├── shelvr/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app factory
│   ├── config.py                  # pydantic-settings config loader
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                # declarative base, engine setup
│   │   ├── session.py             # async session factory
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── book.py
│   │       ├── author.py
│   │       ├── series.py
│   │       ├── tag.py
│   │       ├── format.py
│   │       ├── identifier.py
│   │       ├── user.py
│   │       ├── device.py
│   │       ├── reading_progress.py
│   │       ├── job.py
│   │       └── plugin_data.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── books.py               # start with one, add as needed
│   ├── schemas/                   # pydantic request/response models
│   │   ├── __init__.py
│   │   └── book.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                # shared FastAPI dependencies
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # aggregates all v1 routers
│   │   │   ├── auth.py
│   │   │   ├── books.py
│   │   │   ├── server_info.py
│   │   │   ├── opds.py
│   │   │   └── plugins.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt.py
│   │   └── password.py
│   ├── formats/                   # format reader implementations
│   │   ├── __init__.py
│   │   ├── base.py                # FormatReader protocol
│   │   ├── epub.py
│   │   ├── pdf.py
│   │   └── mobi.py
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── base.py                # Plugin base class
│   │   ├── context.py             # PluginContext
│   │   ├── manifest.py            # plugin.toml parser
│   │   ├── loader.py              # discovery, load, lifecycle
│   │   └── registry.py            # in-memory registry of loaded plugins
│   ├── import_/
│   │   ├── __init__.py
│   │   └── pipeline.py            # orchestrates the import flow
│   ├── services/
│   │   ├── __init__.py
│   │   ├── covers.py              # thumbnail generation
│   │   └── hashing.py             # file hashing
│   └── logging_config.py
├── plugins/                       # user-installed plugins live here
│   └── .gitkeep
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    │   └── books/                 # sample EPUB/PDF/MOBI files for tests
    ├── unit/
    └── integration/
```

## Day 1 plan — what I want you to build right now

Do these in order. Stop after each numbered step and show me the work before moving on.

### Step 1: Project skeleton

Create:

- `pyproject.toml` with dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]>=2.0`, `aiosqlite`, `alembic`, `pydantic>=2`, `pydantic-settings`, `python-jose[cryptography]`, `passlib[argon2]`, `structlog`, `httpx`, `tomli` (stdlib `tomllib` on 3.11+). Dev deps: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`.
- `README.md` with a one-paragraph project description, the AGPL license notice, and a "status: pre-alpha" banner.
- `LICENSE` containing AGPL-3.0 full text.
- `.gitignore` (Python standard + `.venv/`, `shelvr.db*`, `*.toml.local`, `/plugins/*/` except `.gitkeep`).
- `.github/workflows/ci.yml` running `ruff check`, `ruff format --check`, `mypy shelvr`, and `pytest` on pushes and PRs.
- Empty directory structure matching the layout above (use `.gitkeep` files for empty dirs).

### Step 2: Config system

Implement `shelvr/config.py` using `pydantic-settings`. Settings I need:

- `host: str = "127.0.0.1"` (bind to localhost by default — explicit opt-in for LAN)
- `port: int = 7654`
- `library_path: Path` (required)
- `database_url: str` (default: `sqlite+aiosqlite:///shelvr.db`)
- `plugin_dir: Path = Path("plugins")`
- `log_level: str = "INFO"`
- `jwt_secret: str` (required; fail loudly if missing)
- `jwt_access_ttl_minutes: int = 15`
- `jwt_refresh_ttl_days: int = 30`

Load order: defaults → `shelvr.toml` → environment variables with `SHELVR_` prefix.

Ship a `shelvr.toml.example` in the repo root with commented-out explanations of every setting.

### Step 3: Database foundation

- `shelvr/db/base.py`: async engine + declarative base.
- `shelvr/db/session.py`: `get_session()` async generator for FastAPI `Depends`.
- All models from the directory structure above, matching the schema documented in the strategy doc (I'll paste it separately if needed, but you have the structure).
- Alembic configured for async + autogenerate.
- One migration creating all v1 tables.

Key model details:

- `books.sort_title` is a computed-style field populated by the app on insert/update.
- `formats` has a UNIQUE constraint on `file_hash` (global dedup).
- `identifiers` has a composite UNIQUE on `(book_id, scheme, value)`.
- `plugin_data` has a composite UNIQUE on `(plugin_id, key)`.
- Timestamps use `TIMESTAMP` with server-default `CURRENT_TIMESTAMP`.

### Step 4: Minimal API — `/api/v1/server/info`

- FastAPI app factory in `shelvr/main.py`.
- Health endpoint at `/api/v1/server/info` returning `{version, protocol_version, features}` where `features` is a list the API will grow over time (v1: `["opds", "plugins", "jwt_auth"]`).
- `structlog` configured with request ID middleware.
- `uvicorn` entry point in `pyproject.toml` so I can run `shelvr` from the command line.

### Step 5: Stop and check in

Show me what you built, run the test suite, and wait for me to review before moving to format readers.

## What NOT to do on day 1

- Don't build the plugin system yet — that's day 4.
- Don't write format readers yet — that's day 2.
- Don't build the web UI — that's day 6.
- Don't add authentication beyond the config secret scaffolding — full JWT auth lands day 7.
- Don't create stub files for things we haven't discussed. Empty directories with `.gitkeep` are fine; placeholder modules that claim to do something are not.
- Don't add dependencies beyond what I listed without asking me first.
- Don't write "TODO" comments in place of real decisions. If you hit a decision point, surface it as a question to me.

## How I want you to communicate

- **Before writing code**, confirm you understand the step and call out anything ambiguous or that seems wrong to you.
- **While writing code**, narrate briefly — just enough that I can follow what you're choosing and why.
- **After each step**, summarize what you built, what you chose to leave for later, and any decisions you made that I should know about.
- **Push back** if I'm asking for something that will hurt future-us. I'd rather hear "this will make step 4 harder, consider doing X instead" than discover it myself in a week.

## Reference material

The full strategy doc (architecture, roadmap through v3, plugin API philosophy, pricing, LibraryIQ relationship, etc.) is in `docs/STRATEGY.md`. When in doubt about a design decision, check there first. If it isn't covered, ask me.

Ready when you are. Start with Step 1.

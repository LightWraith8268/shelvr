# Shelvr

> **Status:** Pre-alpha. The server runs and is feature-complete enough for daily use, but the data model, API, and on-disk layout are still subject to breaking change without migration paths.

Shelvr is a self-hosted ebook library server with a Plex-style split: an always-on background service holds your library and exposes a REST API, and any number of clients — the bundled web UI, third-party OPDS readers, and (eventually) Android and Tauri desktop apps — connect to it.

Part of the [Ink & Iron Apps](https://inknironapps.com) product lineup.

## What ships today

- **Library management.** Upload EPUB / PDF / MOBI / AZW3, dedupe by SHA-256, extract metadata + covers, organize by tags, authors, language, and series.
- **Web UI.** Login, faceted library grid, book detail with cover, multi-format download, admin upload (drag-drop), admin metadata edit, admin delete, admin bulk delete, plugin admin page, account / change-password page, series detail page, in-browser EPUB reader (epub.js) with reading-progress sync, native PDF reader.
- **REST API** under `/api/v1/`. JWT bearer auth with refresh-token rotation. Roles: `admin` and `reader`. Per-user reading progress tracked server-side and resumed across devices.
- **OPDS 1.2 catalog** at `/api/v1/opds`. Root navigation, paginated `/all`, plus browse-by-tag and browse-by-author. Accepts HTTP Basic auth so KOReader, Moon+ Reader, and Aldiko work without bespoke OAuth.
- **Plugin system from day one.** Built-in EPUB / PDF / MOBI format readers ship as plugins. Reference `hello_world` plugin lives in-tree. Admins can enable / disable plugins from the web UI; flags persist in the database.
- **First-party CLI.** `shelvr serve` starts the API. `shelvr user create <username> [--admin]` bootstraps accounts.

See [CHANGELOG.md](./CHANGELOG.md) for the per-release history.

## Architecture (one paragraph)

The server (`shelvrd`, Python + FastAPI + async SQLAlchemy + SQLite) is the only canonical store. SQLite is configured for WAL and runs on the local filesystem; the library directory holds the actual ebook files in a `Author/Book/` layout with sized cover thumbnails alongside. The web UI is a React + Vite SPA whose built bundle (`web/dist/`) is committed to the repo so a server install needs no Node toolchain — FastAPI serves the SPA shell at `/` and falls back to `index.html` for any non-API path so the client-side router can take over. Plugin discovery loads built-in plugins from `shelvr/plugins/builtin/` plus any user-installed plugins under `settings.plugin_dir`, into a single registry that owns event dispatch with priority ordering and per-plugin error isolation.

For the longer version see [docs/STRATEGY.md](./docs/STRATEGY.md) and the [v1 design spec](./docs/superpowers/specs/2026-04-17-shelvr-v1-client-and-plugin-design.md).

## Quick start (development)

Requires Python 3.11+ and Git. Node is **only** needed if you want to rebuild the web UI from source — the committed `web/dist/` is what the server ships.

```bash
# 1. Clone and install
git clone https://github.com/LightWraith8268/shelvr.git
cd shelvr
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"   # PowerShell / Git Bash on Windows
# or: source .venv/bin/activate && pip install -e ".[dev]"  # macOS / Linux

# 2. Configure (minimum — set a JWT secret and a library directory)
export SHELVR_JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
export SHELVR_LIBRARY_PATH=$HOME/Shelvr-Library
mkdir -p "$SHELVR_LIBRARY_PATH"

# 3. Migrate the database
.venv/Scripts/alembic upgrade head

# 4. Bootstrap an admin account
.venv/Scripts/python.exe -m shelvr.cli user create alice --admin

# 5. Run the server (binds 127.0.0.1:7654 by default)
.venv/Scripts/python.exe -m uvicorn shelvr.main:create_app --factory
```

Open `http://127.0.0.1:7654/`, sign in as `alice`, and upload a book.

### Configuration precedence

`shelvr.toml` (in the working directory) → `SHELVR_*` environment variables (env wins). All settings live on `shelvr.config.Settings`. The bind address defaults to `127.0.0.1`; LAN exposure is opt-in via `SHELVR_HOST=0.0.0.0`.

## Connecting an OPDS reader

Point your reader at `http://<host>:7654/api/v1/opds` and supply your Shelvr username + password as HTTP Basic credentials. Tested with KOReader; should work with any OPDS 1.2-compliant client.

## Development workflow

```bash
.venv/Scripts/pytest                  # 238+ tests, all sync + async
.venv/Scripts/ruff check . && .venv/Scripts/ruff format --check .
.venv/Scripts/mypy shelvr             # strict mode
.venv/Scripts/alembic revision --autogenerate -m "..."
```

Continuous integration runs lint + types + tests on Python 3.11 and 3.12. Pushes to `claude/dev` auto-merge to `main` via `.github/workflows/auto-merge.yml`; pushes to `main` cut a release via `.github/workflows/release.yml` which derives the semver bump from conventional commit prefixes (`feat:` → minor, `fix:` / `perf:` → patch, `!` → major) and uploads the sdist + wheel to a GitHub Release.

## License

AGPL-3.0-only. See [LICENSE](./LICENSE).

The server is free and open source. AGPL-3.0 protects against commercial repackaging — anyone forking Shelvr to offer it as a hosted service must also open-source their modifications. The eventual paid Android client is a separate work distributed under its own terms and communicates with the server only over the public REST API, so it doesn't trigger AGPL's copyleft on the server.

## Documentation

- [Strategy and architecture](./docs/STRATEGY.md)
- [Kickoff plan](./docs/KICKOFF.md)
- [v1 design spec](./docs/superpowers/specs/2026-04-17-shelvr-v1-client-and-plugin-design.md)
- [Changelog](./CHANGELOG.md)

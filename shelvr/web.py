"""Mount the built React SPA onto the FastAPI app.

The web frontend is built into ``web/dist/`` (committed in the repo so that a
server install needs no Node toolchain). At runtime we serve ``index.html``
for any path that isn't an API call and hand the rest off to the SPA's
client-side router.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def mount_web(app: FastAPI, dist_dir: Path) -> None:
    """Wire the SPA's static bundle onto the API app.

    No-ops when ``dist_dir`` doesn't exist (e.g. running tests against a tree
    that hasn't been built yet).
    """
    if not dist_dir.is_dir():
        return

    index_html = dist_dir / "index.html"
    if not index_html.is_file():
        return

    resolved_dist = dist_dir.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        if full_path:
            candidate = (resolved_dist / full_path).resolve()
            if _is_within(candidate, resolved_dist) and candidate.is_file():
                return FileResponse(candidate)

        return FileResponse(index_html)

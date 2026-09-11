# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Main FastAPI application entrypoint for tro. system.

Serves both the REST API (under /api/v1 and /api/v1/auth) and the compiled
React SPA (frontend/dist) from a single port when the frontend has been built.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

from .api import router as api_router
from .auth import router as auth_router
from .compat import CORSMiddleware, FastAPI, FileResponse, HTMLResponse, HTTPException, StaticFiles
from .database import init_db

# Resolve path to the compiled frontend build output (frontend/dist/)
DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
DIST_INDEX = DIST_DIR / "index.html"
ASSETS_DIR = DIST_DIR / "assets"


@asynccontextmanager
async def lifespan(app: Any) -> AsyncGenerator[None, None]:
    """Lifespan context manager that initializes database tables on server startup."""
    init_db()
    yield


app = FastAPI(title="tro. API", lifespan=lifespan)

# Configure CORS middleware allowing requests from React Vite frontend (port 5173) and other origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach routers to the application
app.include_router(auth_router)
app.include_router(api_router)

# Mount static assets directory if present (Vite builds into frontend/dist/assets)
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint confirming application readiness and health status."""
    return {"status": "healthy", "app": "tro."}


# ---------------------------------------------------------------------------
# Static file serving & SPA fallback
# ---------------------------------------------------------------------------

def _read_index_html() -> str:
    """Read the compiled index.html content."""
    try:
        return DIST_INDEX.read_text(encoding="utf-8")
    except OSError:
        raise HTTPException(status_code=500, detail="Failed to read index.html")


@app.get("/")
def serve_root() -> Any:
    """Serve the SPA index.html or a friendly JSON hint when frontend is not built."""
    if DIST_INDEX.exists():
        return HTMLResponse(content=_read_index_html(), status_code=200)
    # Headless / dev mode: frontend not built yet.
    return {
        "app": "tro.",
        "status": "running",
        "api": "/api/v1",
        "message": (
            "Frontend not built. Run `npm run build` inside the `frontend/` "
            "directory to enable the web interface."
        ),
    }


@app.get("/{full_path:path}")
def serve_spa(full_path: str) -> Any:
    """Catch-all route that serves the SPA for all non-API, non-asset paths.

    API paths (/api/...) and health check (/health) are intentionally excluded
    and must never be swallowed by the SPA catch-all handler.
    """
    # Protect API, health, and static asset namespaces – do not silently absorb.
    if (
        full_path == "api"
        or full_path.startswith("api/")
        or full_path == "health"
        or full_path.startswith("health/")
        or full_path == "assets"
        or full_path.startswith("assets/")
    ):
        raise HTTPException(status_code=404, detail="Not Found")

    # Guard against directory traversal attacks before inspecting dist status.
    try:
        candidate = (DIST_DIR / full_path).resolve()
        candidate.relative_to(DIST_DIR.resolve())
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=404, detail="Not Found")

    if candidate.is_file():
        return FileResponse(str(candidate))

    if not DIST_INDEX.exists():
        # Frontend not built; return JSON hint instead of 404.
        return {
            "app": "tro.",
            "status": "running",
            "api": "/api/v1",
            "message": (
                "Frontend not built. Run `npm run build` inside the `frontend/` "
                "directory to enable the web interface."
            ),
        }

    # SPA fallback: serve index.html for client-side routing paths such as
    # /login, /dashboard, /verify/<token>.
    return HTMLResponse(content=_read_index_html(), status_code=200)

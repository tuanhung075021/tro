# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Unified launcher for the tro. application.

Starts the backend API server (FastAPI/Uvicorn) and serves the compiled
React SPA from the same port.  Database tables are initialised automatically
before the server accepts connections.

Usage::

    python run.py [--host HOST] [--port PORT] [--reload] [--no-open]

Environment variables (lower priority than CLI flags):

    HOST   – listening address (default: 0.0.0.0)
    PORT   – listening port    (default: 8000)
"""

import argparse
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the launcher CLI."""
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="tro. – Single-port launcher (API + SPA).",
    )
    env_host = os.environ.get("HOST", "").strip() or "0.0.0.0"
    env_port_raw = os.environ.get("PORT", "").strip()
    try:
        env_port = int(env_port_raw) if env_port_raw else 8000
    except ValueError:
        env_port = 8000

    parser.add_argument(
        "--host",
        default=env_host,
        help="Bind address (default: env HOST or 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=env_port,
        help="Listening port (default: env PORT or 8000).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable live-reload for development (default: False).",
    )
    parser.add_argument(
        "--no-open",
        dest="no_open",
        action="store_true",
        default=False,
        help="Do not automatically open a browser window on startup.",
    )
    parser.add_argument(
        "--build-frontend",
        dest="build_frontend",
        action="store_true",
        default=False,
        help="Run `npm run build` inside frontend/ before starting the server.",
    )
    return parser


def _check_frontend(build: bool = False) -> None:
    """Check whether the frontend has been built; optionally trigger npm build."""
    repo_root = Path(__file__).resolve().parent
    dist_index = repo_root / "frontend" / "dist" / "index.html"

    if dist_index.exists():
        return  # Already built – nothing to do.

    if build:
        import subprocess
        frontend_dir = repo_root / "frontend"
        print("[tro.] Frontend build not found – running `npm run build` …")
        try:
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=str(frontend_dir),
                check=False,
                shell=(sys.platform == "win32"),
            )
            if result.returncode != 0:
                print(
                    "[tro.] WARNING: `npm run build` exited with code "
                    f"{result.returncode}. The server will start in headless mode.",
                    file=sys.stderr,
                )
        except (FileNotFoundError, OSError) as exc:
            print(
                f"[tro.] WARNING: Could not run `npm run build` ({exc}). "
                "The server will start in headless mode.",
                file=sys.stderr,
            )
        return

    # Print a friendly hint only – do not block startup.
    print(
        "[tro.] INFO: Frontend build not found at frontend/dist/index.html.\n"
        "       The API is fully operational. To enable the web interface run:\n"
        "         cd frontend && npm run build\n"
        "       then restart this launcher.",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list | None = None) -> None:
    """Parse CLI arguments, initialise the database, and start Uvicorn."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Ensure the project root is importable regardless of CWD.
    repo_root = str(Path(__file__).resolve().parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Initialise the database (idempotent).
    from backend.app.database import init_db  # noqa: PLC0415
    print("[tro.] Initialising database …")
    init_db()

    # Check / build frontend.
    _check_frontend(build=args.build_frontend)

    # Automatically open the browser unless --no-open was specified.
    if not args.no_open:
        import threading
        import webbrowser

        open_host = "127.0.0.1" if args.host in ("0.0.0.0", "") else args.host
        open_url = f"http://{open_host}:{args.port}"

        def _open_browser() -> None:
            import time
            time.sleep(1.0)
            try:
                webbrowser.open(open_url)
            except Exception:
                pass

        threading.Thread(target=_open_browser, daemon=True).start()

    # Import uvicorn here so the module can be imported without it installed
    # (e.g. in pure unit-test environments).
    try:
        import uvicorn  # noqa: PLC0415
    except ImportError:
        print(
            "[tro.] ERROR: uvicorn is not installed.\n"
            "       Install it with: pip install uvicorn[standard]",
            file=sys.stderr,
        )
        sys.exit(1)

    url = f"http://{args.host}:{args.port}"
    print(f"[tro.] Starting server on {url} (reload={args.reload})")

    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

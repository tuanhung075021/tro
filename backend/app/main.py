# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""Main FastAPI application entrypoint for tro system."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from .api import router as api_router
from .auth import router as auth_router
from .compat import CORSMiddleware, FastAPI
from .database import init_db


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


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint confirming application readiness and health status."""
    return {"status": "healthy", "app": "tro."}

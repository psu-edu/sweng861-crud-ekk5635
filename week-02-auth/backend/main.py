"""FastAPI application for Week 2 — authentication and protected APIs.

Week 1 shipped an unauthenticated Hello/Health service. This service is where
the Google OIDC login flow, the local user store, and the `requireAuth`
middleware are built; `/api/hello` becomes a protected endpoint here.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure the users table exists before the first request is served.

    Run on startup rather than at import time so that importing this module —
    which the tests do — neither needs a database nor creates one.
    """
    create_tables()
    yield


app = FastAPI(
    title="SWENG 861 Week 2 — Auth API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Deliberately unauthenticated: a monitor has no login."""
    return {"status": "ok"}

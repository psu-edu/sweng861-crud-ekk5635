"""FastAPI application for Week 2 — authentication and protected APIs.

Week 1 shipped an unauthenticated Hello/Health service. This service is where
the Google OIDC login flow, the local user store, and the `requireAuth`
middleware are built; `/api/hello` becomes a protected endpoint here.
"""

from fastapi import FastAPI

app = FastAPI(title="SWENG 861 Week 2 — Auth API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Deliberately unauthenticated: a monitor has no login."""
    return {"status": "ok"}

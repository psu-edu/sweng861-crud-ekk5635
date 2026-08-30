"""Health and hello endpoints for the SWENG 861 CRUD project.

This is the entry point that later grows into the AnalysisNote CRUD API.
"""

from fastapi import FastAPI

app = FastAPI(title="SWENG 861 CRUD API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the process is up. Used as a liveness probe."""
    return {"status": "ok"}


@app.get("/api/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello, World!"}

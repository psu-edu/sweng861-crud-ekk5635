"""Test setup shared by every test in this service.

The environment is populated here, before anything imports config, so the
suite never reads the developer's .env and never depends on a real Google
client. Tests that need a token sign one with the key set below.
"""

import os

import pytest

# load_dotenv() does not overwrite variables that already exist, so setting
# these first means .env cannot leak real credentials into a test run.
os.environ.update(
    {
        "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_REDIRECT_URI": "http://localhost:8000/auth/callback",
        "SESSION_JWT_SECRET": "test-signing-key-used-only-by-the-test-suite",
        "SESSION_JWT_TTL_SECONDS": "3600",
        # Never connected to. Nothing in these tests reaches the database.
        "DATABASE_URL": "postgresql+psycopg://unused:unused@localhost:5432/unused",
    }
)


@pytest.fixture(scope="session")
def client():
    """A client for the app, with no startup event and so no database.

    Starlette runs lifespan only for a TestClient used as a context manager.
    Constructing one plainly is deliberate: the protected endpoint reads the
    caller's identity out of the token and touches no table, so these tests
    prove the gate rather than the infrastructure, and they run in CI with no
    services started.
    """
    from fastapi.testclient import TestClient

    from main import app

    return TestClient(app)


@pytest.fixture
def valid_token() -> str:
    """A session token exactly as /auth/callback issues one."""
    from models import User
    from tokens import issue_session_token

    # Not persisted: issue_session_token reads only the id and the email.
    return issue_session_token(User(id=7, email="student@psu.edu"))

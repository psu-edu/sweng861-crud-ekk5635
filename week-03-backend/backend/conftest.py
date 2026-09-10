"""Test setup shared by every test in this service.

The environment is populated here, before anything imports config, so the
suite never reads the developer's .env and never depends on a real Google
client. Tests that need a token sign one with the key set below.

Most of the suite touches no database. The few tests that do read
TEST_DATABASE_URL from the real environment and skip when it is unset, so a
checkout with no Postgres still runs everything else. It is deliberately a
different database from the one the application uses: the demo rows are what
the screenshots and the Postman collection point at, and a test run that
truncated them would destroy submission evidence.
"""

import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Read .env before the fake values below are set, so TEST_DATABASE_URL is
# available while DATABASE_URL is still overridden.
load_dotenv()
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

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
        # SEC requires a contact address on every request. A test must never
        # send the developer's real one to data.sec.gov.
        "SEC_USER_AGENT": "SWENG861 Test Suite test@example.invalid",
    }
)


@pytest.fixture(scope="session")
def client():
    """A client for the app, which needs no database.

    The protected endpoint reads the caller's identity out of the token and
    touches no table, so these tests prove the gate rather than the
    infrastructure and run in CI with no services started. Since the schema
    moved to Alembic the app has no startup hook either.
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


# ---------------------------------------------------------------------------
# Database fixtures, used only by tests that assert what a constraint does
# ---------------------------------------------------------------------------

needs_db = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set"
)


@pytest.fixture(scope="session")
def db_engine():
    """An engine against the test database, with the schema migrated on.

    The schema is created from the models rather than by running Alembic. The
    migrations are verified separately, against the real database, and making
    every test run pay for three revisions would buy nothing here.
    """
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set")

    from sqlalchemy import create_engine

    from models import Base

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """A session whose work is rolled back when the test ends.

    Each test therefore starts from an empty table without truncating anything,
    and two tests cannot see each other's rows.
    """
    from sqlalchemy.orm import Session

    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def coverage(db_session):
    """One user holding one coverage of Tesla, matching the captured fixtures."""
    from models import Coverage, User

    user = User(google_sub="test-subject", email="analyst@psu.edu")
    db_session.add(user)
    db_session.flush()

    row = Coverage(
        owner_id=user.id, title="Tesla, Inc.", ticker="TSLA", cik="0001318605"
    )
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def assets_client():
    """A client answering every request with the captured Tesla Assets document."""
    import httpx

    payload = json.loads(
        (Path(__file__).parent / "tests" / "fixtures" / "tesla_assets_200.json").read_text()
    )
    return httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    )

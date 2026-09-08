"""Engine, session factory, and the FastAPI request-scoped session.

Everything here is built lazily for the same reason config.get_settings() is:
importing this module must not require a populated .env or a running database,
or the Part D tests could not import the application.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings
from models import Base


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """One connection pool per process."""
    return create_engine(
        get_settings().database_url,
        # Checks a pooled connection before handing it out. Without this, the
        # first request after the database container restarts fails on a
        # connection the pool still believes is alive.
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def create_tables() -> None:
    """Create any table that does not exist yet.

    Enough for Week 2, where the schema is one table and does not change. Once
    Week 3 starts altering columns this has to become a migration tool
    (Alembic): create_all only adds, it never modifies an existing table.
    """
    Base.metadata.create_all(get_engine())


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()

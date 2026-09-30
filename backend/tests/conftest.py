"""Shared pytest fixtures for API-level tests.

By default this uses a single shared in-memory SQLite database
(StaticPool keeps the same connection alive across the several
short-lived sessions FastAPI opens per request) so tests do not depend
on a running PostgreSQL instance.

When `TEST_DATABASE_URL` is set, the same tests run against a real
PostgreSQL database whose schema is built by **applying the Alembic
migrations**, not by `Base.metadata.create_all()`. That combination is
what actually closes CRD-004: it exercises the migration chain and the
production engine on every test, rather than only on the dedicated
migration tests. Tables are truncated between tests to keep them
isolated while paying the migration cost only once per session.

    $env:TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:55432/context_rot_test"
    pytest
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _alembic_config(url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.attributes["sqlalchemy_url"] = url
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture(scope="session")
def _postgres_engine() -> Generator[Engine]:
    """A migrated PostgreSQL database, built once for the whole session."""
    assert TEST_DATABASE_URL is not None
    engine = create_engine(TEST_DATABASE_URL)
    config = _alembic_config(TEST_DATABASE_URL)
    # Start from a known-empty database so a leftover schema from an
    # earlier run cannot mask a broken migration.
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    try:
        yield engine
    finally:
        command.downgrade(config, "base")
        engine.dispose()


def _truncate_all(engine: Engine) -> None:
    # Migration tests in this suite deliberately downgrade the schema, so
    # rebuild it if a previous test left the database empty.
    inspector = inspect(engine)
    if not inspector.has_table("agent_sessions"):
        assert TEST_DATABASE_URL is not None
        command.upgrade(_alembic_config(TEST_DATABASE_URL), "head")

    table_names = ", ".join(
        f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables)
    )
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(request: pytest.FixtureRequest) -> Generator[TestClient]:
    if TEST_DATABASE_URL:
        engine = request.getfixturevalue("_postgres_engine")
        _truncate_all(engine)
        owns_engine = False
    else:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        owns_engine = True

    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db() -> Generator[Session]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        if owns_engine:
            Base.metadata.drop_all(engine)
            engine.dispose()

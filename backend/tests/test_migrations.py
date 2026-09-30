"""Migration tests (CRD-004).

Two layers, deliberately separated:

* The offline tests always run. They need no database and catch the
  failure modes that do not require one: a broken/branched revision
  chain, a missing downgrade, or a migration that cannot even be
  rendered to SQL.

* The PostgreSQL tests only run when `TEST_DATABASE_URL` is set. They
  are the ones that actually matter for CRD-004, because they apply the
  real migration chain to a real PostgreSQL database and then diff the
  result against `Base.metadata`. Model/migration drift has already
  happened twice in this repository's history (the
  `detection_events.metadata` column and two `context_health_scores`
  columns existed in the models before a migration created them), and
  nothing in the suite would have caught it: the rest of the tests build
  their schema with `Base.metadata.create_all()`, which never executes a
  migration at all.

Run the PostgreSQL layer with, for example:

    $env:TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/context_rot_test"
    pytest tests/test_migrations.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app.models import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

postgres_required = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set TEST_DATABASE_URL to a disposable PostgreSQL database to run "
    "the migration tests against a real engine.",
)


def _alembic_config(url: str | None = None) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    if url is not None:
        config.attributes["sqlalchemy_url"] = url
        config.set_main_option("sqlalchemy.url", url)
    return config


# --------------------------------------------------------------------------
# Offline checks -- always run.
# --------------------------------------------------------------------------


def test_migration_chain_has_exactly_one_head() -> None:
    """A branched chain silently leaves half the schema unapplied."""
    script = ScriptDirectory.from_config(_alembic_config())

    assert len(script.get_heads()) == 1


def test_migration_chain_is_linear_and_connected() -> None:
    """Every revision must be reachable from base to head."""
    script = ScriptDirectory.from_config(_alembic_config())
    head = script.get_current_head()

    revisions = list(script.walk_revisions("base", head))

    assert len(revisions) == len(set(r.revision for r in revisions))
    # walk_revisions yields head..base; the last one must be the root.
    assert revisions[-1].down_revision is None


def test_every_migration_defines_a_downgrade() -> None:
    """A migration without a downgrade cannot be rolled back in an incident."""
    script = ScriptDirectory.from_config(_alembic_config())

    missing = []
    for revision in script.walk_revisions():
        source = Path(revision.path).read_text(encoding="utf-8")
        body = source.split("def downgrade()", 1)
        if len(body) != 2 or "pass" == body[1].split("\n", 1)[1].strip():
            missing.append(revision.revision)

    assert missing == []


def test_full_chain_renders_to_sql_offline() -> None:
    """Catches migrations that cannot be rendered (e.g. bad op arguments)."""
    config = _alembic_config("postgresql+psycopg2://user:pass@localhost/db")

    # Raises if any revision in the chain fails to render.
    command.upgrade(config, "head", sql=True)


# --------------------------------------------------------------------------
# PostgreSQL checks -- the real CRD-004 coverage.
# --------------------------------------------------------------------------


@pytest.fixture
def postgres_engine():
    """A database this test module may freely upgrade and downgrade.

    Teardown leaves the schema back at head rather than at base: the
    shared session fixture in `conftest.py` runs the rest of the suite
    against this same database, and would otherwise find its tables
    dropped depending on test ordering.
    """
    assert TEST_DATABASE_URL is not None
    engine = create_engine(TEST_DATABASE_URL, poolclass=None)
    config = _alembic_config(TEST_DATABASE_URL)
    command.downgrade(config, "base")
    try:
        yield engine
    finally:
        command.upgrade(config, "head")
        engine.dispose()


@postgres_required
def test_migrations_upgrade_to_head_on_postgres(postgres_engine) -> None:
    config = _alembic_config(TEST_DATABASE_URL)

    command.upgrade(config, "head")

    tables = set(inspect(postgres_engine).get_table_names())
    assert "agent_sessions" in tables
    assert "analysis_runs" in tables
    assert "detection_events" in tables


@postgres_required
def test_migrated_schema_matches_models_exactly(postgres_engine) -> None:
    """The drift test: migrations must produce what the ORM declares.

    This is what would have caught the two historical drifts, and what
    keeps `Base.metadata.create_all()` in the rest of the suite honest.
    """
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    command.upgrade(_alembic_config(TEST_DATABASE_URL), "head")

    with postgres_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        diff = compare_metadata(context, Base.metadata)

    assert diff == [], f"Model/migration drift detected: {diff}"


@postgres_required
def test_migrations_are_reversible_on_postgres(postgres_engine) -> None:
    """A downgrade that fails makes an incident rollback impossible."""
    config = _alembic_config(TEST_DATABASE_URL)
    command.upgrade(config, "head")

    command.downgrade(config, "base")

    remaining = set(inspect(postgres_engine).get_table_names()) - {"alembic_version"}
    assert remaining == set()


@postgres_required
def test_upgrade_downgrade_upgrade_round_trip(postgres_engine) -> None:
    config = _alembic_config(TEST_DATABASE_URL)

    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    tables = set(inspect(postgres_engine).get_table_names())
    assert "analysis_runs" in tables


@postgres_required
def test_failed_detectors_column_exists_after_migration(postgres_engine) -> None:
    """Phase 1 added this column; it must exist via migration, not only ORM."""
    command.upgrade(_alembic_config(TEST_DATABASE_URL), "head")

    columns = {c["name"] for c in inspect(postgres_engine).get_columns("analysis_runs")}
    assert "failed_detectors" in columns

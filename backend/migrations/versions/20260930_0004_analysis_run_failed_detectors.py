"""Record which detectors failed during an analysis run.

Before this migration a detector that raised was logged and silently
dropped: the run was still persisted as `completed`, and any health
dimension whose only signals came from the failed detector scored a
perfect 1.0. A transient LLM outage therefore made a session look
*healthier*, which inverts the product's core promise.

`failed_detectors` records the detectors that did not complete so the
run's status (`partial`/`failed`) and its unassessed health dimensions
can be reported honestly instead of being reported as clean.

Revision ID: 20260930_0004
Revises: 20260917_0003
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260930_0004"
down_revision: str | Sequence[str] | None = "20260917_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column(
            "failed_detectors",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    # The server-side default only exists to backfill pre-existing rows
    # (which predate failure tracking and are therefore recorded as
    # having no known failures); new rows always supply an explicit
    # value via the ORM, matching the other JSON columns in this schema.
    op.alter_column("analysis_runs", "failed_detectors", server_default=None)


def downgrade() -> None:
    op.drop_column("analysis_runs", "failed_detectors")

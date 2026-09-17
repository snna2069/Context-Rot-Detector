"""Add a metadata column to detection_events.

Phase 5's semantic detectors already compute detector-specific detail
(most notably the evidence-based `classification` behind an
`UNSUPPORTED_CLAIM` signal, e.g. "possible_hallucination") but it was
only ever available transiently on the in-memory `Signal`, never
persisted. Phase 7's hallucination-analysis dashboard view needs to
render that classification, so it is now stored as a small JSON column
rather than reconstructed or guessed in the UI.

Revision ID: 20260917_0003
Revises: 20260914_0002
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260917_0003"
down_revision: str | Sequence[str] | None = "20260914_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "detection_events",
        sa.Column(
            "metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
    )
    # The server-side default only exists to backfill pre-existing rows;
    # new rows always supply an explicit value via the ORM, matching the
    # other JSON metadata columns in this schema.
    op.alter_column("detection_events", "metadata", server_default=None)


def downgrade() -> None:
    op.drop_column("detection_events", "metadata")

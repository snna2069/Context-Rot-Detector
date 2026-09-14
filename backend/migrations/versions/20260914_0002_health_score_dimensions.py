"""Expand context_health_scores with Phase 6 scoring dimensions.

`evidence_coverage_score` is renamed to `tool_utilization_score` (it only
ever measured tool-result misuse; "unsupported claim" signals now have
their own dedicated dimension) and two new sub-scores are added:
`information_retention_score` (previously-established facts being lost
or omitted) and `hallucination_risk_score` (evidence-based claim-support
classifications from the Phase 5 semantic layer).

Revision ID: 20260914_0002
Revises: 20260911_0001
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0002"
down_revision: str | Sequence[str] | None = "20260911_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "context_health_scores",
        "evidence_coverage_score",
        new_column_name="tool_utilization_score",
    )
    op.add_column(
        "context_health_scores",
        sa.Column("information_retention_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "context_health_scores",
        sa.Column("hallucination_risk_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("context_health_scores", "hallucination_risk_score")
    op.drop_column("context_health_scores", "information_retention_score")
    op.alter_column(
        "context_health_scores",
        "tool_utilization_score",
        new_column_name="evidence_coverage_score",
    )

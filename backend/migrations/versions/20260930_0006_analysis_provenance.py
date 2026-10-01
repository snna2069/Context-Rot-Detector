"""Persist prompt/provider provenance for analysis runs.

Revision ID: 20260930_0006
Revises: 20260930_0005
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260930_0006"
down_revision: str | Sequence[str] | None = "20260930_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column(
            "prompt_version",
            sa.String(length=100),
            nullable=False,
            server_default="semantic-prompts-v2",
        ),
    )
    op.add_column("analysis_runs", sa.Column("provider_name", sa.String(length=100)))
    op.add_column("analysis_runs", sa.Column("model_name", sa.String(length=200)))
    op.add_column(
        "analysis_runs",
        sa.Column("llm_call_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("analysis_runs", "prompt_version", server_default=None)
    op.alter_column("analysis_runs", "llm_call_count", server_default=None)


def downgrade() -> None:
    op.drop_column("analysis_runs", "llm_call_count")
    op.drop_column("analysis_runs", "model_name")
    op.drop_column("analysis_runs", "provider_name")
    op.drop_column("analysis_runs", "prompt_version")

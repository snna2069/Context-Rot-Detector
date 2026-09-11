"""Create the initial Context Rot Detector domain schema.

Revision ID: 20260911_0001
Revises:
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260911_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_sessions_status_updated_at",
        "agent_sessions",
        ["status", "updated_at"],
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("message_metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "sequence_number", name="uq_messages_session_sequence"
        ),
    )
    op.create_index(
        "ix_messages_session_created_at", "messages", ["session_id", "created_at"]
    )
    op.create_index("ix_messages_session_role", "messages", ["session_id", "role"])

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("call_index", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=200), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id", "call_index", name="uq_tool_calls_message_index"
        ),
    )
    op.create_index(
        "ix_tool_calls_session_created_at", "tool_calls", ["session_id", "created_at"]
    )

    op.create_table(
        "tool_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("tool_call_id", sa.String(length=36), nullable=False),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("is_error", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tool_call_id"], ["tool_calls.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tool_call_id"),
    )
    op.create_index(
        "ix_tool_results_session_created_at",
        "tool_results",
        ["session_id", "created_at"],
    )

    op.create_table(
        "context_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_context_snapshots_session_created_at",
        "context_snapshots",
        ["session_id", "created_at"],
    )

    op.create_table(
        "important_facts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("source_message_id", sa.String(length=36), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("predicate", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_facts_confidence"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"], ["messages.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_important_facts_session_status",
        "important_facts",
        ["session_id", "status"],
    )
    op.create_index(
        "ix_important_facts_session_subject",
        "important_facts",
        ["session_id", "subject"],
    )

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_version", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("input_sequence_start", sa.Integer(), nullable=True),
        sa.Column("input_sequence_end", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_runs_session_created_at",
        "analysis_runs",
        ["session_id", "created_at"],
    )

    op.create_table(
        "detection_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("detection_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_detection_confidence"
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_detection_events_session_timestamp",
        "detection_events",
        ["session_id", "timestamp"],
    )
    op.create_index(
        "ix_detection_events_type_severity",
        "detection_events",
        ["detection_type", "severity"],
    )

    op.create_table(
        "context_health_scores",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("consistency_score", sa.Float(), nullable=True),
        sa.Column("instruction_adherence_score", sa.Float(), nullable=True),
        sa.Column("evidence_coverage_score", sa.Float(), nullable=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "overall_score >= 0 AND overall_score <= 1", name="ck_health_overall_score"
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["agent_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_context_health_scores_session_measured_at",
        "context_health_scores",
        ["session_id", "measured_at"],
    )

    op.create_table(
        "important_fact_conflicts",
        sa.Column("fact_id", sa.String(length=36), nullable=False),
        sa.Column("conflicting_fact_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["conflicting_fact_id"], ["important_facts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["fact_id"], ["important_facts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("fact_id", "conflicting_fact_id"),
    )

    op.create_table(
        "detection_event_messages",
        sa.Column("detection_event_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["detection_event_id"], ["detection_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("detection_event_id", "message_id"),
    )

    op.create_table(
        "detection_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("detection_event_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=True),
        sa.Column("tool_call_id", sa.String(length=36), nullable=True),
        sa.Column("tool_result_id", sa.String(length=36), nullable=True),
        sa.Column("context_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("important_fact_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_role", sa.String(length=50), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["context_snapshot_id"], ["context_snapshots.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["detection_event_id"], ["detection_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["important_fact_id"], ["important_facts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tool_call_id"], ["tool_calls.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tool_result_id"], ["tool_results.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_detection_evidence_detection_event",
        "detection_evidence",
        ["detection_event_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_detection_evidence_detection_event", table_name="detection_evidence"
    )
    op.drop_table("detection_evidence")
    op.drop_table("detection_event_messages")
    op.drop_table("important_fact_conflicts")
    op.drop_index(
        "ix_context_health_scores_session_measured_at",
        table_name="context_health_scores",
    )
    op.drop_table("context_health_scores")
    op.drop_index("ix_detection_events_type_severity", table_name="detection_events")
    op.drop_index(
        "ix_detection_events_session_timestamp", table_name="detection_events"
    )
    op.drop_table("detection_events")
    op.drop_index("ix_analysis_runs_session_created_at", table_name="analysis_runs")
    op.drop_table("analysis_runs")
    op.drop_index("ix_important_facts_session_subject", table_name="important_facts")
    op.drop_index("ix_important_facts_session_status", table_name="important_facts")
    op.drop_table("important_facts")
    op.drop_index(
        "ix_context_snapshots_session_created_at", table_name="context_snapshots"
    )
    op.drop_table("context_snapshots")
    op.drop_index("ix_tool_results_session_created_at", table_name="tool_results")
    op.drop_table("tool_results")
    op.drop_index("ix_tool_calls_session_created_at", table_name="tool_calls")
    op.drop_table("tool_calls")
    op.drop_index("ix_messages_session_role", table_name="messages")
    op.drop_index("ix_messages_session_created_at", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_agent_sessions_status_updated_at", table_name="agent_sessions")
    op.drop_table("agent_sessions")

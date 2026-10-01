"""Add indexes for duplicate checks and run/timeline query patterns.

Revision ID: 20260930_0005
Revises: 20260930_0004
Create Date: 2026-09-30
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260930_0005"
down_revision: str | Sequence[str] | None = "20260930_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_agent_sessions_created_at",
        "agent_sessions",
        ["created_at"],
    )
    op.create_index(
        "ix_messages_session_provider_message_id",
        "messages",
        ["session_id", "provider_message_id"],
    )
    op.create_index(
        "ix_tool_calls_session_call_index",
        "tool_calls",
        ["session_id", "call_index"],
    )
    op.create_index(
        "ix_detection_events_analysis_run_id",
        "detection_events",
        ["analysis_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_detection_events_analysis_run_id", table_name="detection_events")
    op.drop_index("ix_tool_calls_session_call_index", table_name="tool_calls")
    op.drop_index("ix_messages_session_provider_message_id", table_name="messages")
    op.drop_index("ix_agent_sessions_created_at", table_name="agent_sessions")

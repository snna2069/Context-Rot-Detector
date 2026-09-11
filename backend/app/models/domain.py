from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class MessageRole(StrEnum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class FactStatus(StrEnum):
    PROPOSED = "proposed"
    VERIFIED = "verified"
    CONFLICTING = "conflicting"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class DetectionSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionType(StrEnum):
    CONTRADICTION = "contradiction"
    INSTRUCTION_DRIFT = "instruction_drift"
    STALE_CONTEXT = "stale_context"
    REPETITION = "repetition"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    TOOL_RESULT_MISUSE = "tool_result_misuse"


class AnalysisRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


important_fact_conflicts = Table(
    "important_fact_conflicts",
    Base.metadata,
    Column(
        "fact_id",
        ForeignKey("important_facts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "conflicting_fact_id",
        ForeignKey("important_facts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

detection_event_messages = Table(
    "detection_event_messages",
    Base.metadata,
    Column(
        "detection_event_id",
        ForeignKey("detection_events.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "message_id", ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    ),
)


class AgentSession(Base):
    __tablename__ = "agent_sessions"
    __table_args__ = (
        Index("ix_agent_sessions_status_updated_at", "status", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        String(20), default=SessionStatus.ACTIVE, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    session_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    messages: Mapped[list[Message]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.sequence_number",
    )
    tool_calls: Mapped[list[ToolCall]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    tool_results: Mapped[list[ToolResult]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    context_snapshots: Mapped[list[ContextSnapshot]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    important_facts: Mapped[list[ImportantFact]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    detection_events: Mapped[list[DetectionEvent]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    health_scores: Mapped[list[ContextHealthScore]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    analysis_runs: Mapped[list[AnalysisRun]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "sequence_number", name="uq_messages_session_sequence"
        ),
        Index("ix_messages_session_created_at", "session_id", "created_at"),
        Index("ix_messages_session_role", "session_id", "role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[MessageRole] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    message_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    session: Mapped[AgentSession] = relationship(back_populates="messages")
    tool_calls: Mapped[list[ToolCall]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )
    source_facts: Mapped[list[ImportantFact]] = relationship(
        back_populates="source_message"
    )
    detection_events: Mapped[list[DetectionEvent]] = relationship(
        secondary=detection_event_messages, back_populates="related_messages"
    )


class ToolCall(Base):
    __tablename__ = "tool_calls"
    __table_args__ = (
        Index("ix_tool_calls_session_created_at", "session_id", "created_at"),
        UniqueConstraint(
            "message_id", "call_index", name="uq_tool_calls_message_index"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[str] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    call_index: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(200), nullable=False)
    arguments: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    session: Mapped[AgentSession] = relationship(back_populates="tool_calls")
    message: Mapped[Message] = relationship(back_populates="tool_calls")
    result: Mapped[ToolResult | None] = relationship(
        back_populates="tool_call", uselist=False, cascade="all, delete-orphan"
    )


class ToolResult(Base):
    __tablename__ = "tool_results"
    __table_args__ = (
        Index("ix_tool_results_session_created_at", "session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False
    )
    tool_call_id: Mapped[str] = mapped_column(
        ForeignKey("tool_calls.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_error: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    session: Mapped[AgentSession] = relationship(back_populates="tool_results")
    tool_call: Mapped[ToolCall] = relationship(back_populates="result")


class ContextSnapshot(Base):
    __tablename__ = "context_snapshots"
    __table_args__ = (
        Index("ix_context_snapshots_session_created_at", "session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    session: Mapped[AgentSession] = relationship(back_populates="context_snapshots")


class ImportantFact(Base):
    __tablename__ = "important_facts"
    __table_args__ = (
        Index("ix_important_facts_session_status", "session_id", "status"),
        Index("ix_important_facts_session_subject", "session_id", "subject"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_facts_confidence"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False
    )
    source_message_id: Mapped[str] = mapped_column(
        ForeignKey("messages.id", ondelete="RESTRICT"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    predicate: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[FactStatus] = mapped_column(
        String(20), default=FactStatus.PROPOSED, nullable=False
    )
    fact_metadata: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    session: Mapped[AgentSession] = relationship(back_populates="important_facts")
    source_message: Mapped[Message] = relationship(back_populates="source_facts")
    conflicting_facts: Mapped[list[ImportantFact]] = relationship(
        secondary=important_fact_conflicts,
        primaryjoin=id == important_fact_conflicts.c.fact_id,
        secondaryjoin=id == important_fact_conflicts.c.conflicting_fact_id,
        back_populates="conflicted_by",
    )
    conflicted_by: Mapped[list[ImportantFact]] = relationship(
        secondary=important_fact_conflicts,
        primaryjoin=id == important_fact_conflicts.c.conflicting_fact_id,
        secondaryjoin=id == important_fact_conflicts.c.fact_id,
        back_populates="conflicting_facts",
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        Index("ix_analysis_runs_session_created_at", "session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False
    )
    analysis_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AnalysisRunStatus] = mapped_column(
        String(20), default=AnalysisRunStatus.PENDING, nullable=False
    )
    input_sequence_start: Mapped[int | None] = mapped_column(Integer)
    input_sequence_end: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped[AgentSession] = relationship(back_populates="analysis_runs")
    detection_events: Mapped[list[DetectionEvent]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )
    health_scores: Mapped[list[ContextHealthScore]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )


class DetectionEvent(Base):
    __tablename__ = "detection_events"
    __table_args__ = (
        Index("ix_detection_events_session_timestamp", "session_id", "timestamp"),
        Index("ix_detection_events_type_severity", "detection_type", "severity"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_detection_confidence"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False
    )
    analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    detection_type: Mapped[DetectionType] = mapped_column(String(40), nullable=False)
    severity: Mapped[DetectionSeverity] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    session: Mapped[AgentSession] = relationship(back_populates="detection_events")
    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="detection_events")
    related_messages: Mapped[list[Message]] = relationship(
        secondary=detection_event_messages, back_populates="detection_events"
    )
    evidence: Mapped[list[DetectionEvidence]] = relationship(
        back_populates="detection_event", cascade="all, delete-orphan"
    )


class DetectionEvidence(Base):
    __tablename__ = "detection_evidence"
    __table_args__ = (
        Index("ix_detection_evidence_detection_event", "detection_event_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    detection_event_id: Mapped[str] = mapped_column(
        ForeignKey("detection_events.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE")
    )
    tool_call_id: Mapped[str | None] = mapped_column(
        ForeignKey("tool_calls.id", ondelete="CASCADE")
    )
    tool_result_id: Mapped[str | None] = mapped_column(
        ForeignKey("tool_results.id", ondelete="CASCADE")
    )
    context_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("context_snapshots.id", ondelete="CASCADE")
    )
    important_fact_id: Mapped[str | None] = mapped_column(
        ForeignKey("important_facts.id", ondelete="CASCADE")
    )
    evidence_role: Mapped[str] = mapped_column(String(50), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)

    detection_event: Mapped[DetectionEvent] = relationship(back_populates="evidence")


class ContextHealthScore(Base):
    __tablename__ = "context_health_scores"
    __table_args__ = (
        Index(
            "ix_context_health_scores_session_measured_at", "session_id", "measured_at"
        ),
        CheckConstraint(
            "overall_score >= 0 AND overall_score <= 1", name="ck_health_overall_score"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False
    )
    analysis_run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    overall_score: Mapped[float] = mapped_column(nullable=False)
    relevance_score: Mapped[float | None] = mapped_column()
    consistency_score: Mapped[float | None] = mapped_column()
    instruction_adherence_score: Mapped[float | None] = mapped_column()
    evidence_coverage_score: Mapped[float | None] = mapped_column()
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    session: Mapped[AgentSession] = relationship(back_populates="health_scores")
    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="health_scores")

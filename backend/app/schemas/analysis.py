"""Response schemas for the analysis engine's persisted output.

There are no request schemas here beyond triggering `POST
/sessions/{id}/analyze` with no body -- the engine derives everything it
needs from the session's own stored messages/tool calls/tool results, so
callers do not supply analysis parameters in this first version.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import AnalysisRunStatus, DetectionSeverity, DetectionType


class DetectionEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str | None
    tool_call_id: str | None
    tool_result_id: str | None
    context_snapshot_id: str | None
    important_fact_id: str | None
    evidence_role: str
    excerpt: str | None


class DetectionEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    analysis_run_id: str
    detection_type: DetectionType
    severity: DetectionSeverity
    confidence: float
    explanation: str
    timestamp: datetime
    evidence: list[DetectionEvidenceRead] = []
    related_message_ids: list[str] = []
    metadata: dict[str, Any] = {}

    @staticmethod
    def from_orm_event(event) -> DetectionEventRead:  # noqa: ANN001
        """Build the response model explicitly rather than via `model_validate`.

        Two fields cannot be picked up automatically by
        `from_attributes`: `related_message_ids` is derived from a
        relationship of full `Message` objects, and the persisted
        metadata column is named `event_metadata` in Python (to avoid
        colliding with SQLAlchemy's own `Base.metadata` class attribute,
        which would otherwise shadow it and break naive attribute
        lookup) but is exposed to API consumers simply as `metadata`.
        """
        return DetectionEventRead(
            id=event.id,
            session_id=event.session_id,
            analysis_run_id=event.analysis_run_id,
            detection_type=event.detection_type,
            severity=event.severity,
            confidence=event.confidence,
            explanation=event.explanation,
            timestamp=event.timestamp,
            evidence=[DetectionEvidenceRead.model_validate(e) for e in event.evidence],
            related_message_ids=[m.id for m in event.related_messages],
            metadata=dict(event.event_metadata),
        )


class ContextHealthScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    analysis_run_id: str
    overall_score: float
    relevance_score: float | None
    consistency_score: float | None
    instruction_adherence_score: float | None
    information_retention_score: float | None
    tool_utilization_score: float | None
    hallucination_risk_score: float | None
    measured_at: datetime


class AnalysisRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    analysis_version: str
    status: AnalysisRunStatus
    input_sequence_start: int | None
    input_sequence_end: int | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class AnalysisRunResult(BaseModel):
    """The full response returned by `POST /sessions/{id}/analyze`."""

    analysis_run: AnalysisRunRead
    detection_events: list[DetectionEventRead]
    health_score: ContextHealthScoreRead | None


class HealthTrendPointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    measured_at: datetime
    overall_score: float
    context_length: int | None


class HealthChangeExplanationRead(BaseModel):
    """Reasons behind the most recent health-score change.

    `reasons` lists only categories whose detection-event count strictly
    increased between the two most recent analysis runs; it is always a
    subset of, and traceable back to, the underlying `DetectionEvent` rows
    -- never a free-form LLM summary.
    """

    direction: str
    score_delta: float | None
    reasons: list[str]
    headline: str


class HealthTrendRead(BaseModel):
    """Response for `GET /sessions/{id}/health-trend`.

    `direction` and `summary` are derived, not independently verified,
    from a simple linear trend over the session's own recorded
    checkpoints -- see `app.analysis.health_trend` for the (deliberately
    simple, non-statistical) regression that produces them. `explanation`
    covers only the most recent checkpoint-to-checkpoint change.
    """

    direction: str
    slope_per_checkpoint: float
    slope_per_context_length: float | None
    is_degrading_with_length: bool
    summary: str
    points: list[HealthTrendPointRead]
    explanation: HealthChangeExplanationRead

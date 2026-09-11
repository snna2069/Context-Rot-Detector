"""Response schemas for the analysis engine's persisted output.

There are no request schemas here beyond triggering `POST
/sessions/{id}/analyze` with no body -- the engine derives everything it
needs from the session's own stored messages/tool calls/tool results, so
callers do not supply analysis parameters in this first version.
"""

from __future__ import annotations

from datetime import datetime

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

    @staticmethod
    def from_orm_event(event) -> DetectionEventRead:  # noqa: ANN001
        """Build the response model, flattening `related_messages` to IDs.

        Kept as an explicit adapter (rather than a plain `model_validate`)
        because `related_message_ids` is derived from a relationship of
        full `Message` objects, not a column that `from_attributes` can
        pick up automatically.
        """
        read = DetectionEventRead.model_validate(event)
        return read.model_copy(
            update={
                "related_message_ids": [m.id for m in event.related_messages],
            }
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
    evidence_coverage_score: float | None
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

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from app.models import (
    AnalysisRun,
    ContextHealthScore,
    DetectionEvent,
    DetectionEvidence,
    DetectionType,
)


def create_run(db: DBSession, analysis_run: AnalysisRun) -> AnalysisRun:
    db.add(analysis_run)
    db.flush()
    return analysis_run


def create_detection_event(
    db: DBSession, detection_event: DetectionEvent
) -> DetectionEvent:
    db.add(detection_event)
    db.flush()
    return detection_event


def create_detection_evidence(
    db: DBSession, evidence: DetectionEvidence
) -> DetectionEvidence:
    db.add(evidence)
    db.flush()
    return evidence


def create_health_score(
    db: DBSession, health_score: ContextHealthScore
) -> ContextHealthScore:
    db.add(health_score)
    db.flush()
    return health_score


def get_run_by_id(db: DBSession, analysis_run_id: str) -> AnalysisRun | None:
    stmt = (
        select(AnalysisRun)
        .where(AnalysisRun.id == analysis_run_id)
        .options(
            selectinload(AnalysisRun.detection_events).selectinload(
                DetectionEvent.evidence
            ),
            selectinload(AnalysisRun.detection_events).selectinload(
                DetectionEvent.related_messages
            ),
            selectinload(AnalysisRun.health_scores),
        )
    )
    return db.scalar(stmt)


def list_detection_events_by_session(
    db: DBSession, session_id: str
) -> list[DetectionEvent]:
    stmt = (
        select(DetectionEvent)
        .where(DetectionEvent.session_id == session_id)
        .order_by(DetectionEvent.timestamp.desc())
        .options(
            selectinload(DetectionEvent.evidence),
            selectinload(DetectionEvent.related_messages),
        )
    )
    return list(db.scalars(stmt))


def list_health_scores_by_session(
    db: DBSession, session_id: str
) -> list[ContextHealthScore]:
    stmt = (
        select(ContextHealthScore)
        .where(ContextHealthScore.session_id == session_id)
        .order_by(ContextHealthScore.measured_at.desc())
        .options(selectinload(ContextHealthScore.analysis_run))
    )
    return list(db.scalars(stmt))


def list_detection_types_by_run(
    db: DBSession, analysis_run_id: str
) -> list[DetectionType]:
    """The `detection_type` of every event from one analysis run.

    Used by `app.analysis.health_explain` to compare how many signals of
    each type fired in one run versus the previous one -- deliberately
    just the types (not full rows), since that is all the explanation
    logic needs.
    """
    stmt = select(DetectionEvent.detection_type).where(
        DetectionEvent.analysis_run_id == analysis_run_id
    )
    return list(db.scalars(stmt))

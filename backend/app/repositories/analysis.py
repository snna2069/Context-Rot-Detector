from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import aliased, selectinload

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


def count_detection_events_by_sessions(
    db: DBSession,
    session_ids: list[str],
    *,
    detection_type: DetectionType | None = None,
) -> dict[str, int]:
    """Total detection-event count per session, in one query.

    Optionally filtered to a single `detection_type` (used by the
    dashboard to surface an at-a-glance "hallucination signal count" per
    session, counting only `UNSUPPORTED_CLAIM` events).
    """
    if not session_ids:
        return {}
    stmt = select(DetectionEvent.session_id, func.count(DetectionEvent.id)).where(
        DetectionEvent.session_id.in_(session_ids)
    )
    if detection_type is not None:
        stmt = stmt.where(DetectionEvent.detection_type == detection_type)
    stmt = stmt.group_by(DetectionEvent.session_id)
    return dict(db.execute(stmt).all())


def latest_health_scores_by_sessions(
    db: DBSession, session_ids: list[str]
) -> dict[str, ContextHealthScore]:
    """The most recent `ContextHealthScore` row per session, in one query.

    Uses a `ROW_NUMBER()` window function (partitioned per session,
    ordered newest-first) rather than one "latest score" query per
    session, so the dashboard's session list stays a small, bounded
    number of queries regardless of how many sessions are on the page.
    """
    if not session_ids:
        return {}
    row_number = (
        func.row_number()
        .over(
            partition_by=ContextHealthScore.session_id,
            order_by=ContextHealthScore.measured_at.desc(),
        )
        .label("row_number")
    )
    ranked = (
        select(ContextHealthScore, row_number)
        .where(ContextHealthScore.session_id.in_(session_ids))
        .subquery()
    )
    latest = aliased(ContextHealthScore, ranked)
    stmt = select(latest).where(ranked.c.row_number == 1)
    return {score.session_id: score for score in db.scalars(stmt)}

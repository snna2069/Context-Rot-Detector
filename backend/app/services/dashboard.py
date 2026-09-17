"""Read-only aggregation for the Phase 7 dashboard's session list.

The sessions list view needs, per session, data that lives across three
tables (message count, latest health score, detection-event counts). This
module exists purely to assemble that summary with a small, bounded
number of queries per page of sessions -- it does not introduce any new
business rules, and it never computes or infers anything that isn't
already stored by ingestion/analysis.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session as DBSession

from app.models import AgentSession, ContextHealthScore, DetectionType
from app.repositories import analysis as analysis_repo
from app.repositories import messages as messages_repo
from app.repositories import sessions as sessions_repo


@dataclass(frozen=True)
class SessionOverview:
    session: AgentSession
    message_count: int
    detection_event_count: int
    unsupported_claim_count: int
    latest_health_score: ContextHealthScore | None


def list_session_overviews(
    db: DBSession, *, limit: int = 50, offset: int = 0
) -> list[SessionOverview]:
    sessions = sessions_repo.list_all(db, limit=limit, offset=offset)
    session_ids = [session.id for session in sessions]

    message_counts = messages_repo.count_by_sessions(db, session_ids)
    detection_counts = analysis_repo.count_detection_events_by_sessions(db, session_ids)
    unsupported_claim_counts = analysis_repo.count_detection_events_by_sessions(
        db, session_ids, detection_type=DetectionType.UNSUPPORTED_CLAIM
    )
    latest_scores = analysis_repo.latest_health_scores_by_sessions(db, session_ids)

    return [
        SessionOverview(
            session=session,
            message_count=message_counts.get(session.id, 0),
            detection_event_count=detection_counts.get(session.id, 0),
            unsupported_claim_count=unsupported_claim_counts.get(session.id, 0),
            latest_health_score=latest_scores.get(session.id),
        )
        for session in sessions
    ]

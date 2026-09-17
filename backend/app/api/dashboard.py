"""Aggregated read endpoints for the Phase 7 dashboard.

Kept as its own router (prefix `/dashboard`, not `/sessions`) rather than
adding another route onto the sessions router: `/sessions/{session_id}`
already matches any single path segment after `/sessions/`, so a route
like `/sessions/overview` would either collide with it or depend on
router-registration order. A distinct prefix avoids that entirely.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.schemas.analysis import ContextHealthScoreRead
from app.schemas.dashboard import SessionOverviewRead
from app.schemas.sessions import AgentSessionRead
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/sessions", response_model=list[SessionOverviewRead])
def list_session_overviews(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: DBSession = Depends(get_db),
) -> list[SessionOverviewRead]:
    overviews = dashboard_service.list_session_overviews(db, limit=limit, offset=offset)
    return [
        SessionOverviewRead(
            session=AgentSessionRead.model_validate(overview.session),
            message_count=overview.message_count,
            detection_event_count=overview.detection_event_count,
            unsupported_claim_count=overview.unsupported_claim_count,
            latest_health_score=(
                ContextHealthScoreRead.model_validate(overview.latest_health_score)
                if overview.latest_health_score is not None
                else None
            ),
        )
        for overview in overviews
    ]

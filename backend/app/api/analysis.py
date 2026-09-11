from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.schemas.analysis import (
    AnalysisRunRead,
    AnalysisRunResult,
    ContextHealthScoreRead,
    DetectionEventRead,
)
from app.services import analysis as analysis_service

router = APIRouter(prefix="/sessions", tags=["analysis"])


@router.post("/{session_id}/analyze", response_model=AnalysisRunResult, status_code=201)
def analyze_session(
    session_id: str, db: DBSession = Depends(get_db)
) -> AnalysisRunResult:
    run = analysis_service.run_analysis(db, session_id)
    health_score = run.health_scores[0] if run.health_scores else None
    return AnalysisRunResult(
        analysis_run=AnalysisRunRead.model_validate(run),
        detection_events=[
            DetectionEventRead.from_orm_event(event) for event in run.detection_events
        ],
        health_score=(
            ContextHealthScoreRead.model_validate(health_score)
            if health_score is not None
            else None
        ),
    )


@router.get("/{session_id}/detection-events", response_model=list[DetectionEventRead])
def list_detection_events(
    session_id: str, db: DBSession = Depends(get_db)
) -> list[DetectionEventRead]:
    events = analysis_service.list_detection_events(db, session_id)
    return [DetectionEventRead.from_orm_event(event) for event in events]


@router.get("/{session_id}/health-scores", response_model=list[ContextHealthScoreRead])
def list_health_scores(
    session_id: str, db: DBSession = Depends(get_db)
) -> list[ContextHealthScoreRead]:
    scores = analysis_service.list_health_scores(db, session_id)
    return [ContextHealthScoreRead.model_validate(score) for score in scores]

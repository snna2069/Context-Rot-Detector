"""Persistence orchestration for the context-analysis engine.

This is the only module that bridges the pure, DB-free `app.analysis`
package to the database: it loads a session's stored messages/tool
calls/tool results, builds a `SessionContext`, runs the `AnalysisEngine`,
and persists the resulting signals and health score as
`DetectionEvent`/`DetectionEvidence`/`ContextHealthScore` rows.
"""

from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from app.analysis.context import build_session_context
from app.analysis.detectors import default_detectors
from app.analysis.engine import AnalysisEngine
from app.analysis.health import HealthScoreWeights
from app.analysis.health_explain import HealthChangeExplanation, explain_health_change
from app.analysis.health_trend import (
    HealthTrendPoint,
    HealthTrendResult,
    analyze_health_trend,
)
from app.analysis.semantic import semantic_detectors
from app.analysis.signals import Signal
from app.config import get_settings
from app.models import (
    AnalysisRun,
    AnalysisRunStatus,
    ContextHealthScore,
    DetectionEvent,
    DetectionEvidence,
    Message,
    utc_now,
)
from app.repositories import analysis as analysis_repo
from app.repositories import messages as messages_repo
from app.repositories import tool_calls as tool_calls_repo
from app.repositories import tool_results as tool_results_repo
from app.services.ingestion import get_session
from app.services.llm.factory import get_analysis_provider
from app.services.llm.provider import AnalysisProvider

# Identifies which version of the detector set produced a given
# `AnalysisRun`. Bump this string whenever detector logic changes in a
# way that would make results non-comparable to earlier runs, so
# `ContextHealthScore` history stays interpretable over time.
ANALYSIS_VERSION = "deterministic-v1+semantic-v1+health-v2"


def run_analysis(
    db: DBSession,
    session_id: str,
    provider: AnalysisProvider | None = None,
    weights: HealthScoreWeights | None = None,
) -> AnalysisRun:
    """Run the analysis engine against a session and persist the results.

    Runs synchronously. The deterministic detectors are fast, in-memory,
    and have no LLM/network calls; the semantic detectors (see
    `app.analysis.semantic`) do call out to `provider`, but each is
    already isolated by the engine's per-detector exception handling and
    bounded by small lookback/lookahead windows, so no background job
    queue is needed for this version either.

    `provider` defaults to `get_analysis_provider()`, which resolves to
    the safe `UnavailableAnalysisProvider` when no LLM is configured --
    semantic detectors are always included, never conditionally skipped,
    because that fallback provider already guarantees they emit nothing
    without a real LLM behind them.

    `weights` defaults to `HealthScoreWeights.from_settings(get_settings())`
    so the relative weighting of each health dimension is configurable via
    environment variables (see `app.config.Settings`) without requiring a
    code change; tests and other callers may inject an explicit
    `HealthScoreWeights` to exercise specific weighting scenarios.
    """
    session = get_session(db, session_id)
    messages = messages_repo.list_by_session(db, session_id)
    tool_calls = tool_calls_repo.list_by_session(db, session_id)
    tool_results = tool_results_repo.list_by_session(db, session_id)

    context = build_session_context(session_id, messages, tool_calls, tool_results)
    provider = provider or get_analysis_provider()
    weights = weights or HealthScoreWeights.from_settings(get_settings())
    engine = AnalysisEngine(
        detectors=[*default_detectors(), *semantic_detectors(provider)],
        weights=weights,
    )
    result = engine.run(context)

    analysis_run = AnalysisRun(
        session_id=session.id,
        analysis_version=ANALYSIS_VERSION,
        status=AnalysisRunStatus.COMPLETED,
        input_sequence_start=messages[0].sequence_number if messages else None,
        input_sequence_end=messages[-1].sequence_number if messages else None,
        completed_at=utc_now(),
    )
    analysis_repo.create_run(db, analysis_run)

    messages_by_id: dict[str, Message] = {m.id: m for m in messages}

    for signal in result.signals:
        _persist_signal(db, session.id, analysis_run.id, signal, messages_by_id)

    analysis_repo.create_health_score(
        db,
        ContextHealthScore(
            session_id=session.id,
            analysis_run_id=analysis_run.id,
            overall_score=result.health_score.overall_score,
            relevance_score=result.health_score.relevance_score,
            consistency_score=result.health_score.consistency_score,
            instruction_adherence_score=(
                result.health_score.instruction_adherence_score
            ),
            information_retention_score=(
                result.health_score.information_retention_score
            ),
            tool_utilization_score=result.health_score.tool_utilization_score,
            hallucination_risk_score=result.health_score.hallucination_risk_score,
            measured_at=utc_now(),
        ),
    )

    db.commit()
    run = analysis_repo.get_run_by_id(db, analysis_run.id)
    assert run is not None  # just created in this same transaction
    return run


def _persist_signal(
    db: DBSession,
    session_id: str,
    analysis_run_id: str,
    signal: Signal,
    messages_by_id: dict[str, Message],
) -> None:
    detection_event = DetectionEvent(
        session_id=session_id,
        analysis_run_id=analysis_run_id,
        detection_type=signal.detection_type,
        severity=signal.severity,
        confidence=signal.confidence,
        explanation=signal.explanation,
        timestamp=utc_now(),
    )
    detection_event.related_messages = [
        messages_by_id[message_id]
        for message_id in signal.related_message_ids
        if message_id in messages_by_id
    ]
    analysis_repo.create_detection_event(db, detection_event)

    for evidence in signal.evidence:
        analysis_repo.create_detection_evidence(
            db,
            DetectionEvidence(
                detection_event_id=detection_event.id,
                message_id=evidence.message_id,
                tool_call_id=evidence.tool_call_id,
                tool_result_id=evidence.tool_result_id,
                evidence_role=evidence.role,
                excerpt=evidence.excerpt,
            ),
        )


def list_detection_events(db: DBSession, session_id: str) -> list[DetectionEvent]:
    get_session(db, session_id)
    return analysis_repo.list_detection_events_by_session(db, session_id)


def list_health_scores(db: DBSession, session_id: str) -> list[ContextHealthScore]:
    get_session(db, session_id)
    return analysis_repo.list_health_scores_by_session(db, session_id)


def get_health_trend(db: DBSession, session_id: str) -> HealthTrendResult:
    """Trend the session's health score across every analysis-run checkpoint.

    Answers "was this session getting worse as it became longer?" by
    regressing `overall_score` against both checkpoint order and, where
    the underlying `AnalysisRun` recorded it, the number of messages
    analyzed at each checkpoint (`context_length`). See
    `app.analysis.health_trend` for the regression itself.
    """
    get_session(db, session_id)
    # Stored newest-first; the trend must be computed oldest-first.
    scores = list(reversed(analysis_repo.list_health_scores_by_session(db, session_id)))
    points = [
        HealthTrendPoint(
            measured_at=score.measured_at,
            overall_score=score.overall_score,
            context_length=(
                score.analysis_run.input_sequence_end
                if score.analysis_run is not None
                else None
            ),
        )
        for score in scores
    ]
    return analyze_health_trend(points)


def explain_latest_health_change(
    db: DBSession, session_id: str
) -> HealthChangeExplanation:
    """Explain the most recent health-score change in plain language.

    Compares the two most recent analysis runs' detection events (by
    type) and reports which problem categories increased, per
    `app.analysis.health_explain.explain_health_change`. Returns an
    `"initial"` explanation when fewer than one analysis run exists yet.
    """
    get_session(db, session_id)
    # Newest-first, as stored.
    scores = analysis_repo.list_health_scores_by_session(db, session_id)
    if not scores:
        return explain_health_change(
            current_overall_score=1.0,
            current_detection_types=[],
            previous_overall_score=None,
        )

    current = scores[0]
    current_types = analysis_repo.list_detection_types_by_run(
        db, current.analysis_run_id
    )

    if len(scores) < 2:
        return explain_health_change(
            current_overall_score=current.overall_score,
            current_detection_types=current_types,
        )

    previous = scores[1]
    previous_types = analysis_repo.list_detection_types_by_run(
        db, previous.analysis_run_id
    )
    return explain_health_change(
        current_overall_score=current.overall_score,
        current_detection_types=current_types,
        previous_overall_score=previous.overall_score,
        previous_detection_types=previous_types,
    )

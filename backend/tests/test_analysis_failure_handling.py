"""Regression tests for silent analysis failure (CRD-001).

Before this suite existed, a detector that raised -- most realistically a
semantic detector hitting an LLM timeout, 429, or outage -- was logged and
dropped. The run was still persisted as `completed`, and every health
dimension covered only by that detector scored a perfect 1.0, so the
session's overall health *increased* precisely when the analysis was least
trustworthy.

These tests pin the corrected contract: a failed detector makes its
dimensions unassessed (`None`), never clean, and the run says so.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.analysis.engine import AnalysisEngine
from app.analysis.health import compute_health_score
from app.analysis.signals import Signal
from app.models import (
    AnalysisRunStatus,
    DetectionSeverity,
    DetectionType,
    MessageRole,
)
from app.services.llm.errors import LLMProviderError
from tests.analysis.helpers import make_context


class _ExplodingDetector:
    """Stands in for a semantic detector whose provider call fails."""

    name = "claim_support"
    detection_types = frozenset({DetectionType.UNSUPPORTED_CLAIM})

    def detect(self, context) -> list[Signal]:  # noqa: ANN001, ARG002
        raise LLMProviderError("provider timed out")


class _HealthyDetector:
    name = "contradiction"
    detection_types = frozenset({DetectionType.CONTRADICTION})

    def detect(self, context) -> list[Signal]:  # noqa: ANN001, ARG002
        return []


def test_failed_detector_dimension_is_unassessed_not_perfect() -> None:
    """The core of CRD-001: unassessed must not be reported as 1.0."""
    engine = AnalysisEngine(detectors=[_HealthyDetector(), _ExplodingDetector()])

    result = engine.run(make_context([]))

    assert result.health_score.hallucination_risk_score is None
    # The detector that did run is still reported normally.
    assert result.health_score.consistency_score == 1.0
    assert "hallucination_risk" in result.health_score.unassessed_dimensions


def test_failed_detector_does_not_inflate_overall_score() -> None:
    """A failed detector must never raise the overall score."""
    all_ok = AnalysisEngine(detectors=[_HealthyDetector()]).run(make_context([]))
    with_failure = AnalysisEngine(
        detectors=[_HealthyDetector(), _ExplodingDetector()]
    ).run(make_context([]))

    assert with_failure.health_score.overall_score is not None
    assert all_ok.health_score.overall_score is not None
    assert with_failure.health_score.overall_score <= all_ok.health_score.overall_score


def test_engine_records_outcome_for_every_detector() -> None:
    engine = AnalysisEngine(detectors=[_HealthyDetector(), _ExplodingDetector()])

    result = engine.run(make_context([]))

    assert len(result.outcomes) == 2
    failed = result.failed_outcomes
    assert [o.detector_name for o in failed] == ["claim_support"]
    assert "LLMProviderError" in (failed[0].error or "")
    assert result.unassessed_types == frozenset({DetectionType.UNSUPPORTED_CLAIM})


def test_all_detectors_failing_yields_no_overall_score() -> None:
    """Nothing was assessed, so there is no number to report."""
    engine = AnalysisEngine(detectors=[_ExplodingDetector()])

    result = engine.run(make_context([]))

    assert result.health_score.overall_score is None


def test_compute_health_score_marks_uncovered_types() -> None:
    """A dimension no completed detector covers is unknown, not clean."""
    score = compute_health_score(
        [],
        None,
        assessed_types=frozenset({DetectionType.TOPIC_DRIFT}),
    )

    assert score.relevance_score == 1.0
    assert score.consistency_score is None
    assert "consistency" in score.unassessed_dimensions


def test_unassessed_dimension_excluded_from_overall_average() -> None:
    """Overall is the average of what was assessed, not of a padded 1.0."""
    signal = Signal(
        detector_name="contradiction",
        detection_type=DetectionType.CONTRADICTION,
        severity=DetectionSeverity.MEDIUM,
        confidence=1.0,
        explanation="contradiction",
    )

    # consistency = 1 - 0.15 = 0.85; five other dimensions are clean at 1.0.
    full = compute_health_score([signal], None)
    assert full.overall_score == pytest.approx((0.85 + 5 * 1.0) / 6, abs=1e-3)

    # With hallucination_risk uncovered, the average is over 5 dimensions
    # rather than silently treating the unknown dimension as perfect.
    every_type_but_claims = frozenset(
        t for t in DetectionType if t is not DetectionType.UNSUPPORTED_CLAIM
    )
    partial = compute_health_score([signal], None, assessed_types=every_type_but_claims)
    assert partial.hallucination_risk_score is None
    assert partial.overall_score == pytest.approx((0.85 + 4 * 1.0) / 5, abs=1e-3)


def _seed_session(client: TestClient) -> str:
    session_id = client.post("/sessions", json={"name": "s"}).json()["id"]
    for i in range(3):
        client.post(
            f"/sessions/{session_id}/messages",
            json={
                "role": MessageRole.ASSISTANT.value,
                "content": f"The timeout is {i} seconds.",
            },
        )
    return session_id


def test_analyze_endpoint_reports_partial_status_when_a_detector_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: the API must not claim a clean COMPLETED run."""
    import app.services.analysis as analysis_service

    def only_failing_semantic(_provider):  # noqa: ANN001, ANN202
        return [_ExplodingDetector()]

    monkeypatch.setattr(analysis_service, "semantic_detectors", only_failing_semantic)

    session_id = _seed_session(client)
    response = client.post(f"/sessions/{session_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    run = body["analysis_run"]

    assert run["status"] == AnalysisRunStatus.PARTIAL.value
    assert run["error_message"] is not None
    assert run["failed_detectors"][0]["detector"] == "claim_support"
    # The dimension the failed detector covered is explicitly unknown.
    assert body["health_score"]["hallucination_risk_score"] is None


def test_analyze_endpoint_reports_failed_when_every_detector_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.analysis as analysis_service

    monkeypatch.setattr(analysis_service, "default_detectors", lambda: [])
    monkeypatch.setattr(
        analysis_service,
        "semantic_detectors",
        lambda _provider: [_ExplodingDetector()],
    )

    session_id = _seed_session(client)
    response = client.post(f"/sessions/{session_id}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["analysis_run"]["status"] == AnalysisRunStatus.FAILED.value
    # No health score is fabricated when nothing could be assessed.
    assert body["health_score"] is None


def test_successful_run_still_reports_completed(client: TestClient) -> None:
    """The happy path must be unchanged by the failure handling."""
    session_id = _seed_session(client)
    response = client.post(f"/sessions/{session_id}/analyze")

    body = response.json()
    assert body["analysis_run"]["status"] == AnalysisRunStatus.COMPLETED.value
    assert body["analysis_run"]["failed_detectors"] == []
    assert body["analysis_run"]["error_message"] is None
    assert body["health_score"] is not None


def test_analysis_runs_endpoint_exposes_failures(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The dashboard needs run status to explain a partial result."""
    import app.services.analysis as analysis_service

    monkeypatch.setattr(
        analysis_service,
        "semantic_detectors",
        lambda _provider: [_ExplodingDetector()],
    )

    session_id = _seed_session(client)
    client.post(f"/sessions/{session_id}/analyze")

    response = client.get(f"/sessions/{session_id}/analysis-runs")

    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["status"] == AnalysisRunStatus.PARTIAL.value
    assert runs[0]["failed_detectors"][0]["detector"] == "claim_support"


def test_analysis_runs_endpoint_returns_newest_first(client: TestClient) -> None:
    session_id = _seed_session(client)
    client.post(f"/sessions/{session_id}/analyze")
    client.post(f"/sessions/{session_id}/analyze")

    runs = client.get(f"/sessions/{session_id}/analysis-runs").json()

    assert len(runs) == 2
    assert runs[0]["created_at"] >= runs[1]["created_at"]


def test_analysis_runs_endpoint_404s_for_unknown_session(
    client: TestClient,
) -> None:
    response = client.get("/sessions/does-not-exist/analysis-runs")

    assert response.status_code == 404

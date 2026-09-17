"""End-to-end test: ingest a session via the API, trigger analysis, and
verify both the API response shape and that results were actually
persisted (retrievable via the list endpoints on a fresh request)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_session(client: TestClient) -> str:
    response = client.post("/sessions", json={"name": "analysis-test-session"})
    assert response.status_code == 201
    return response.json()["id"]


def _add_message(client: TestClient, session_id: str, role: str, content: str) -> None:
    response = client.post(
        f"/sessions/{session_id}/messages", json={"role": role, "content": content}
    )
    assert response.status_code == 201


def test_analyze_session_persists_and_returns_detected_contradiction(
    client: TestClient,
) -> None:
    session_id = _create_session(client)
    _add_message(client, session_id, "user", "When is the deadline?")
    _add_message(client, session_id, "assistant", "The deadline is March 15th.")
    _add_message(client, session_id, "user", "Can you confirm the deadline again?")
    _add_message(client, session_id, "assistant", "The deadline is next Tuesday.")

    response = client.post(f"/sessions/{session_id}/analyze")
    assert response.status_code == 201
    body = response.json()

    assert body["analysis_run"]["session_id"] == session_id
    assert body["analysis_run"]["status"] == "completed"
    assert body["health_score"] is not None
    assert 0.0 <= body["health_score"]["overall_score"] <= 1.0

    contradiction_events = [
        e for e in body["detection_events"] if e["detection_type"] == "contradiction"
    ]
    assert len(contradiction_events) == 1
    event = contradiction_events[0]
    assert 0.0 < event["confidence"] <= 0.85
    assert len(event["related_message_ids"]) == 2
    assert len(event["evidence"]) == 2
    # Deterministic detectors also attach useful contextual metadata (e.g.
    # `external_verification_available`) -- it must be exposed, not lost.
    assert event["metadata"]["external_verification_available"] is False

    # Results must be independently retrievable afterward, not just
    # returned inline from the /analyze call.
    events_response = client.get(f"/sessions/{session_id}/detection-events")
    assert events_response.status_code == 200
    assert len(events_response.json()) >= 1

    scores_response = client.get(f"/sessions/{session_id}/health-scores")
    assert scores_response.status_code == 200
    assert len(scores_response.json()) == 1


def test_analyze_session_with_no_signals_reports_perfect_health(
    client: TestClient,
) -> None:
    session_id = _create_session(client)
    _add_message(client, session_id, "user", "Hello there.")
    _add_message(client, session_id, "assistant", "Hi! How can I help you today?")

    response = client.post(f"/sessions/{session_id}/analyze")
    assert response.status_code == 201
    body = response.json()

    assert body["detection_events"] == []
    assert body["health_score"]["overall_score"] == 1.0


def test_analyze_unknown_session_returns_404(client: TestClient) -> None:
    response = client.post("/sessions/does-not-exist/analyze")
    assert response.status_code == 404


def test_detection_events_and_health_scores_empty_before_analysis(
    client: TestClient,
) -> None:
    session_id = _create_session(client)

    events_response = client.get(f"/sessions/{session_id}/detection-events")
    assert events_response.status_code == 200
    assert events_response.json() == []

    scores_response = client.get(f"/sessions/{session_id}/health-scores")
    assert scores_response.status_code == 200
    assert scores_response.json() == []

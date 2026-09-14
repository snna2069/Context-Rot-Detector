"""API-level tests for `GET /sessions/{id}/health-trend`.

Exercises the endpoint across multiple analysis runs of a session that
grows and degrades over time, proving the trend/explanation are actually
computed from persisted `ContextHealthScore`/`DetectionEvent` rows (not
just unit-tested in isolation against in-memory fixtures).
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_session(client: TestClient) -> str:
    response = client.post("/sessions", json={"name": "health-trend-test-session"})
    assert response.status_code == 201
    return response.json()["id"]


def _add_message(client: TestClient, session_id: str, role: str, content: str) -> None:
    response = client.post(
        f"/sessions/{session_id}/messages", json={"role": role, "content": content}
    )
    assert response.status_code == 201


def test_health_trend_before_any_analysis_reports_not_enough_data(
    client: TestClient,
) -> None:
    session_id = _create_session(client)

    response = client.get(f"/sessions/{session_id}/health-trend")

    assert response.status_code == 200
    body = response.json()
    assert body["direction"] == "stable"
    assert body["points"] == []
    assert body["explanation"]["direction"] == "initial"


def test_health_trend_reflects_degradation_across_multiple_analysis_runs(
    client: TestClient,
) -> None:
    session_id = _create_session(client)

    # First analysis run: healthy, uneventful session.
    _add_message(client, session_id, "user", "Hello there.")
    _add_message(client, session_id, "assistant", "Hi! How can I help you today?")
    first = client.post(f"/sessions/{session_id}/analyze")
    assert first.status_code == 201
    assert first.json()["health_score"]["overall_score"] == 1.0

    # Session grows and a contradiction is introduced before the next run.
    _add_message(client, session_id, "user", "When is the deadline?")
    _add_message(client, session_id, "assistant", "The deadline is March 15th.")
    _add_message(client, session_id, "user", "Can you confirm the deadline again?")
    _add_message(client, session_id, "assistant", "The deadline is next Tuesday.")
    second = client.post(f"/sessions/{session_id}/analyze")
    assert second.status_code == 201
    assert second.json()["health_score"]["overall_score"] < 1.0

    response = client.get(f"/sessions/{session_id}/health-trend")
    assert response.status_code == 200
    body = response.json()

    assert len(body["points"]) == 2
    assert body["direction"] == "degrading"
    assert body["explanation"]["direction"] == "decreased"
    assert "the contradiction rate increased" in body["explanation"]["reasons"]
    assert body["explanation"]["headline"] == "Context health decreased because:"


def test_health_trend_unknown_session_returns_404(client: TestClient) -> None:
    response = client.get("/sessions/does-not-exist/health-trend")
    assert response.status_code == 404

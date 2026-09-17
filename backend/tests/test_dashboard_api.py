"""API-level tests for `GET /dashboard/sessions`.

Exercises the aggregation end-to-end (through ingestion + analyze, not
against hand-built ORM fixtures) so the test also proves the underlying
per-session count/latest-score queries actually join against real rows.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_session(client: TestClient, name: str) -> str:
    response = client.post("/sessions", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _add_message(client: TestClient, session_id: str, role: str, content: str) -> None:
    response = client.post(
        f"/sessions/{session_id}/messages", json={"role": role, "content": content}
    )
    assert response.status_code == 201


def test_dashboard_sessions_empty_when_no_sessions_exist(client: TestClient) -> None:
    response = client.get("/dashboard/sessions")

    assert response.status_code == 200
    assert response.json() == []


def test_dashboard_sessions_reports_zero_counts_before_analysis(
    client: TestClient,
) -> None:
    session_id = _create_session(client, "no-analysis-yet")
    _add_message(client, session_id, "user", "Hello there.")
    _add_message(client, session_id, "assistant", "Hi! How can I help you today?")

    response = client.get("/dashboard/sessions")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    overview = body[0]
    assert overview["session"]["id"] == session_id
    assert overview["message_count"] == 2
    assert overview["detection_event_count"] == 0
    assert overview["unsupported_claim_count"] == 0
    assert overview["latest_health_score"] is None


def test_dashboard_sessions_reflects_latest_analysis(client: TestClient) -> None:
    session_id = _create_session(client, "with-analysis")
    _add_message(client, session_id, "user", "When is the deadline?")
    _add_message(client, session_id, "assistant", "The deadline is March 15th.")
    _add_message(client, session_id, "user", "Can you confirm the deadline again?")
    _add_message(client, session_id, "assistant", "The deadline is next Tuesday.")
    analyze_response = client.post(f"/sessions/{session_id}/analyze")
    assert analyze_response.status_code == 201

    response = client.get("/dashboard/sessions")

    assert response.status_code == 200
    overview = next(o for o in response.json() if o["session"]["id"] == session_id)
    assert overview["message_count"] == 4
    assert overview["detection_event_count"] == 1
    assert overview["unsupported_claim_count"] == 0
    assert overview["latest_health_score"] is not None
    assert 0.0 <= overview["latest_health_score"]["overall_score"] <= 1.0


def test_dashboard_sessions_uses_latest_score_across_multiple_runs(
    client: TestClient,
) -> None:
    session_id = _create_session(client, "multi-run")
    _add_message(client, session_id, "user", "Hello there.")
    _add_message(client, session_id, "assistant", "Hi! How can I help you today?")
    first = client.post(f"/sessions/{session_id}/analyze")
    assert first.status_code == 201
    assert first.json()["health_score"]["overall_score"] == 1.0

    _add_message(client, session_id, "user", "When is the deadline?")
    _add_message(client, session_id, "assistant", "The deadline is March 15th.")
    _add_message(client, session_id, "user", "Can you confirm the deadline again?")
    _add_message(client, session_id, "assistant", "The deadline is next Tuesday.")
    second = client.post(f"/sessions/{session_id}/analyze")
    assert second.status_code == 201
    second_overall_score = second.json()["health_score"]["overall_score"]
    assert second_overall_score < 1.0

    response = client.get("/dashboard/sessions")

    overview = next(o for o in response.json() if o["session"]["id"] == session_id)
    assert overview["latest_health_score"]["overall_score"] == second_overall_score
    # Detection events accumulate across both runs.
    assert overview["detection_event_count"] == 1


def test_dashboard_sessions_respects_pagination(client: TestClient) -> None:
    for i in range(3):
        _create_session(client, f"paginated-{i}")

    response = client.get("/dashboard/sessions", params={"limit": 2, "offset": 0})

    assert response.status_code == 200
    assert len(response.json()) == 2

"""Tests for analysis staleness and read-endpoint pagination.

Staleness (CRD-005): analysis runs only when explicitly triggered, so
messages ingested afterwards are not covered by the stored detections or
health score. The dashboard previously had no way to know that, and so
kept presenting an old score as though it described the whole session.

Pagination (CRD-008): the session-scoped read endpoints previously
returned every row for a session with no bound at all.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models import MessageRole


def _create_session(client: TestClient) -> str:
    return client.post("/sessions", json={"name": "s"}).json()["id"]


def _add_messages(client: TestClient, session_id: str, count: int) -> None:
    for i in range(count):
        response = client.post(
            f"/sessions/{session_id}/messages",
            json={
                "role": MessageRole.ASSISTANT.value,
                "content": f"Message number {i} with some content.",
            },
        )
        assert response.status_code == 201


def test_status_reports_not_analyzed_for_fresh_session(client: TestClient) -> None:
    session_id = _create_session(client)
    _add_messages(client, session_id, 2)

    status = client.get(f"/sessions/{session_id}/analysis-status").json()

    assert status["has_been_analyzed"] is False
    assert status["is_stale"] is False
    assert status["latest_run"] is None
    assert status["message_count"] == 2


def test_status_is_fresh_immediately_after_analysis(client: TestClient) -> None:
    session_id = _create_session(client)
    _add_messages(client, session_id, 3)
    client.post(f"/sessions/{session_id}/analyze")

    status = client.get(f"/sessions/{session_id}/analysis-status").json()

    assert status["has_been_analyzed"] is True
    assert status["is_stale"] is False
    assert status["messages_since_analysis"] == 0
    assert status["analyzed_through_sequence"] == 3


def test_status_becomes_stale_when_messages_arrive_after_analysis(
    client: TestClient,
) -> None:
    """The core of CRD-005."""
    session_id = _create_session(client)
    _add_messages(client, session_id, 3)
    client.post(f"/sessions/{session_id}/analyze")

    _add_messages(client, session_id, 2)

    status = client.get(f"/sessions/{session_id}/analysis-status").json()
    assert status["is_stale"] is True
    assert status["messages_since_analysis"] == 2
    assert status["analyzed_through_sequence"] == 3
    assert status["latest_message_sequence"] == 5


def test_status_returns_fresh_again_after_re_analysis(client: TestClient) -> None:
    session_id = _create_session(client)
    _add_messages(client, session_id, 2)
    client.post(f"/sessions/{session_id}/analyze")
    _add_messages(client, session_id, 2)

    client.post(f"/sessions/{session_id}/analyze")

    status = client.get(f"/sessions/{session_id}/analysis-status").json()
    assert status["is_stale"] is False
    assert status["messages_since_analysis"] == 0


def test_status_handles_analysis_of_an_empty_session(client: TestClient) -> None:
    """A run over zero messages records no sequence range."""
    session_id = _create_session(client)
    client.post(f"/sessions/{session_id}/analyze")

    status = client.get(f"/sessions/{session_id}/analysis-status").json()
    assert status["has_been_analyzed"] is True
    assert status["analyzed_through_sequence"] is None
    assert status["is_stale"] is False

    _add_messages(client, session_id, 1)

    status = client.get(f"/sessions/{session_id}/analysis-status").json()
    assert status["is_stale"] is True
    assert status["messages_since_analysis"] == 1


def test_status_404s_for_unknown_session(client: TestClient) -> None:
    assert client.get("/sessions/nope/analysis-status").status_code == 404


def test_messages_endpoint_supports_limit_and_offset(client: TestClient) -> None:
    session_id = _create_session(client)
    _add_messages(client, session_id, 5)

    first = client.get(f"/sessions/{session_id}/messages?limit=2").json()
    second = client.get(f"/sessions/{session_id}/messages?limit=2&offset=2").json()

    assert [m["sequence_number"] for m in first] == [1, 2]
    assert [m["sequence_number"] for m in second] == [3, 4]


def test_messages_endpoint_rejects_out_of_range_limit(client: TestClient) -> None:
    session_id = _create_session(client)

    assert client.get(f"/sessions/{session_id}/messages?limit=0").status_code == 422
    assert client.get(f"/sessions/{session_id}/messages?limit=5000").status_code == 422
    assert client.get(f"/sessions/{session_id}/messages?offset=-1").status_code == 422


def test_timeline_endpoint_supports_pagination(client: TestClient) -> None:
    session_id = _create_session(client)
    _add_messages(client, session_id, 4)

    body = client.get(f"/sessions/{session_id}/timeline?limit=2&offset=1").json()

    assert [m["sequence_number"] for m in body["messages"]] == [2, 3]
    assert body["session"]["id"] == session_id


def test_detection_events_endpoint_supports_pagination(client: TestClient) -> None:
    session_id = _create_session(client)
    _add_messages(client, session_id, 3)
    client.post(f"/sessions/{session_id}/analyze")

    response = client.get(f"/sessions/{session_id}/detection-events?limit=1")

    assert response.status_code == 200
    assert len(response.json()) <= 1


def test_health_scores_endpoint_supports_pagination(client: TestClient) -> None:
    session_id = _create_session(client)
    _add_messages(client, session_id, 2)
    client.post(f"/sessions/{session_id}/analyze")
    client.post(f"/sessions/{session_id}/analyze")

    all_scores = client.get(f"/sessions/{session_id}/health-scores").json()
    limited = client.get(f"/sessions/{session_id}/health-scores?limit=1").json()

    assert len(all_scores) == 2
    assert len(limited) == 1

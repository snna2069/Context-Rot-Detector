"""Concurrency-conflict tests for ingestion (CRD-007).

Ingestion validates before it inserts: it checks for duplicates and reads
`MAX(sequence_number) + 1` in separate statements from the insert. Two
simultaneous requests for the same session can therefore both pass
validation and collide at the unique constraint.

The collision itself is fine -- the constraint is what guarantees
integrity. What was wrong is how it surfaced: an unhandled
`IntegrityError` became an opaque 500, which tells the client nothing and
does not suggest a retry. These tests pin the corrected behaviour (409).

The race is simulated deterministically by making the pre-insert read
return a stale value, which is exactly what the losing request observes
when another writer commits in between.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models import MessageRole


def _create_session(client: TestClient) -> str:
    return client.post("/sessions", json={"name": "s"}).json()["id"]


def _add_message(client: TestClient, session_id: str, content: str = "hello there"):
    return client.post(
        f"/sessions/{session_id}/messages",
        json={"role": MessageRole.ASSISTANT.value, "content": content},
    )


def test_lost_sequence_number_race_returns_409_not_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = _create_session(client)
    assert _add_message(client, session_id).status_code == 201

    # Simulate a concurrent writer having taken sequence 2 after this
    # request read the last sequence number but before it inserted.
    import app.services.ingestion as ingestion_service

    monkeypatch.setattr(
        ingestion_service.messages_repo, "get_last_sequence_number", lambda *_: 0
    )

    response = _add_message(client, session_id)

    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


def test_lost_tool_call_index_race_returns_409(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = _create_session(client)
    message_id = _add_message(client, session_id).json()["id"]
    first = client.post(
        f"/sessions/{session_id}/messages/{message_id}/tool-calls",
        json={"tool_name": "search", "arguments": {}},
    )
    assert first.status_code == 201

    import app.services.ingestion as ingestion_service

    monkeypatch.setattr(
        ingestion_service.tool_calls_repo, "get_next_call_index", lambda *_: 0
    )

    response = client.post(
        f"/sessions/{session_id}/messages/{message_id}/tool-calls",
        json={"tool_name": "search", "arguments": {}},
    )

    assert response.status_code == 409


def test_lost_tool_result_race_returns_409(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = _create_session(client)
    message_id = _add_message(client, session_id).json()["id"]
    tool_call_id = client.post(
        f"/sessions/{session_id}/messages/{message_id}/tool-calls",
        json={"tool_name": "search", "arguments": {}},
    ).json()["id"]
    assert (
        client.post(
            f"/sessions/{session_id}/tool-calls/{tool_call_id}/result",
            json={"output": {"ok": True}, "is_error": False},
        ).status_code
        == 201
    )

    # The duplicate pre-check passes because it sees no existing result.
    import app.services.ingestion as ingestion_service

    monkeypatch.setattr(
        ingestion_service.tool_results_repo, "get_by_tool_call_id", lambda *_: None
    )

    response = client.post(
        f"/sessions/{session_id}/tool-calls/{tool_call_id}/result",
        json={"output": {"ok": True}, "is_error": False},
    )

    assert response.status_code == 409


def test_conflict_response_does_not_leak_internals(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 409 must be actionable without exposing SQL details."""
    session_id = _create_session(client)
    _add_message(client, session_id)

    import app.services.ingestion as ingestion_service

    monkeypatch.setattr(
        ingestion_service.messages_repo, "get_last_sequence_number", lambda *_: 0
    )

    body = _add_message(client, session_id).json()

    assert "retry" in body["detail"].lower()
    assert "IntegrityError" not in body["detail"]
    assert "INSERT" not in body["detail"].upper()


def test_session_remains_usable_after_a_conflict(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rolled-back conflict must not poison the session."""
    session_id = _create_session(client)
    _add_message(client, session_id)

    import app.services.ingestion as ingestion_service

    monkeypatch.setattr(
        ingestion_service.messages_repo, "get_last_sequence_number", lambda *_: 0
    )
    assert _add_message(client, session_id).status_code == 409

    # Stop simulating the race; the next write should behave normally.
    monkeypatch.undo()

    recovered = _add_message(client, session_id, "a later message")
    assert recovered.status_code == 201
    assert recovered.json()["sequence_number"] == 2

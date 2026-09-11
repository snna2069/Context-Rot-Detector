"""API-level tests for the session ingestion endpoints.

These tests exercise the HTTP layer end to end (routing, validation,
service rules, and error mapping) against an in-memory SQLite database, as
opposed to `test_domain_models.py` which tests the ORM layer directly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_session(client: TestClient, name: str = "Test session") -> dict:
    response = client.post("/sessions", json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_create_and_get_session(client: TestClient) -> None:
    created = _create_session(client, name="Healthy debugging session")

    assert created["name"] == "Healthy debugging session"
    assert created["status"] == "active"
    assert created["session_metadata"] == {}

    response = client.get(f"/sessions/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_session_not_found(client: TestClient) -> None:
    response = client.get("/sessions/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_list_sessions(client: TestClient) -> None:
    _create_session(client, name="First")
    _create_session(client, name="Second")

    response = client.get("/sessions")
    assert response.status_code == 200
    names = {s["name"] for s in response.json()}
    assert {"First", "Second"}.issubset(names)


def test_add_message_auto_sequence(client: TestClient) -> None:
    session = _create_session(client)

    first = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "user", "content": "Hello, agent."},
    )
    second = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "assistant", "content": "Hello, how can I help?"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["sequence_number"] == 1
    assert second.json()["sequence_number"] == 2


def test_add_message_explicit_sequence(client: TestClient) -> None:
    session = _create_session(client)

    response = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "user", "content": "Explicit sequence", "sequence_number": 5},
    )

    assert response.status_code == 201
    assert response.json()["sequence_number"] == 5


def test_add_message_invalid_sequence_ordering(client: TestClient) -> None:
    session = _create_session(client)
    client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "user", "content": "First", "sequence_number": 5},
    )

    response = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "user", "content": "Out of order", "sequence_number": 3},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


def test_add_message_duplicate_provider_id_rejected(client: TestClient) -> None:
    session = _create_session(client)
    payload = {
        "role": "user",
        "content": "Original message",
        "provider_message_id": "provider-abc-123",
    }
    first = client.post(f"/sessions/{session['id']}/messages", json=payload)
    assert first.status_code == 201

    duplicate = client.post(f"/sessions/{session['id']}/messages", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == "conflict"


def test_add_message_to_missing_session(client: TestClient) -> None:
    response = client.post(
        "/sessions/does-not-exist/messages",
        json={"role": "user", "content": "Hello"},
    )
    assert response.status_code == 404


def test_add_message_blank_content_rejected(client: TestClient) -> None:
    session = _create_session(client)

    response = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "user", "content": "   "},
    )

    assert response.status_code == 422


def test_add_message_missing_fields_rejected(client: TestClient) -> None:
    session = _create_session(client)

    response = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "user"},
    )

    assert response.status_code == 422


def test_add_message_invalid_role_rejected(client: TestClient) -> None:
    session = _create_session(client)

    response = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "not-a-real-role", "content": "Hello"},
    )

    assert response.status_code == 422


def test_add_message_oversized_content_rejected(client: TestClient) -> None:
    session = _create_session(client)

    response = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "user", "content": "x" * 60_000},
    )

    assert response.status_code == 422


def test_add_message_oversized_metadata_rejected(client: TestClient) -> None:
    session = _create_session(client)

    response = client.post(
        f"/sessions/{session['id']}/messages",
        json={
            "role": "user",
            "content": "Hello",
            "message_metadata": {"blob": "x" * 25_000},
        },
    )

    assert response.status_code == 422


def test_list_messages_returns_ordered_timeline(client: TestClient) -> None:
    session = _create_session(client)
    for i in range(3):
        client.post(
            f"/sessions/{session['id']}/messages",
            json={"role": "user", "content": f"message {i}"},
        )

    response = client.get(f"/sessions/{session['id']}/messages")
    assert response.status_code == 200
    sequence_numbers = [m["sequence_number"] for m in response.json()]
    assert sequence_numbers == [1, 2, 3]


def test_add_tool_call_auto_index(client: TestClient) -> None:
    session = _create_session(client)
    message = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "assistant", "content": "Let me check that."},
    ).json()

    first = client.post(
        f"/sessions/{session['id']}/messages/{message['id']}/tool-calls",
        json={"tool_name": "search", "arguments": {"query": "weather"}},
    )
    second = client.post(
        f"/sessions/{session['id']}/messages/{message['id']}/tool-calls",
        json={"tool_name": "search", "arguments": {"query": "weather again"}},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["call_index"] == 0
    assert second.json()["call_index"] == 1


def test_add_tool_call_duplicate_index_rejected(client: TestClient) -> None:
    session = _create_session(client)
    message = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "assistant", "content": "Let me check that."},
    ).json()

    payload = {"tool_name": "search", "call_index": 0, "arguments": {}}
    first = client.post(
        f"/sessions/{session['id']}/messages/{message['id']}/tool-calls",
        json=payload,
    )
    duplicate = client.post(
        f"/sessions/{session['id']}/messages/{message['id']}/tool-calls",
        json=payload,
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_add_tool_call_to_missing_message(client: TestClient) -> None:
    session = _create_session(client)

    response = client.post(
        f"/sessions/{session['id']}/messages/does-not-exist/tool-calls",
        json={"tool_name": "search", "arguments": {}},
    )

    assert response.status_code == 404


def test_add_tool_result(client: TestClient) -> None:
    session = _create_session(client)
    message = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "assistant", "content": "Let me check that."},
    ).json()
    tool_call = client.post(
        f"/sessions/{session['id']}/messages/{message['id']}/tool-calls",
        json={"tool_name": "search", "arguments": {"query": "weather"}},
    ).json()

    response = client.post(
        f"/sessions/{session['id']}/tool-calls/{tool_call['id']}/result",
        json={"output": {"temperature_f": 72}, "is_error": False},
    )

    assert response.status_code == 201
    assert response.json()["output"] == {"temperature_f": 72}


def test_add_tool_result_duplicate_rejected(client: TestClient) -> None:
    session = _create_session(client)
    message = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "assistant", "content": "Let me check that."},
    ).json()
    tool_call = client.post(
        f"/sessions/{session['id']}/messages/{message['id']}/tool-calls",
        json={"tool_name": "search", "arguments": {}},
    ).json()

    payload = {"output": {"ok": True}}
    first = client.post(
        f"/sessions/{session['id']}/tool-calls/{tool_call['id']}/result",
        json=payload,
    )
    duplicate = client.post(
        f"/sessions/{session['id']}/tool-calls/{tool_call['id']}/result",
        json=payload,
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_add_tool_result_for_missing_tool_call(client: TestClient) -> None:
    session = _create_session(client)

    response = client.post(
        f"/sessions/{session['id']}/tool-calls/does-not-exist/result",
        json={"output": {}},
    )

    assert response.status_code == 404


def test_get_timeline(client: TestClient) -> None:
    session = _create_session(client)
    message = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "user", "content": "What is the weather?"},
    ).json()
    assistant_message = client.post(
        f"/sessions/{session['id']}/messages",
        json={"role": "assistant", "content": "Let me check."},
    ).json()
    tool_call = client.post(
        f"/sessions/{session['id']}/messages/{assistant_message['id']}/tool-calls",
        json={"tool_name": "search", "arguments": {"query": "weather"}},
    ).json()
    client.post(
        f"/sessions/{session['id']}/tool-calls/{tool_call['id']}/result",
        json={"output": {"temperature_f": 72}},
    )

    response = client.get(f"/sessions/{session['id']}/timeline")

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["id"] == session["id"]
    assert len(body["messages"]) == 2
    assert body["messages"][0]["id"] == message["id"]

    assistant_entry = body["messages"][1]
    assert len(assistant_entry["tool_calls"]) == 1
    assert assistant_entry["tool_calls"][0]["result"]["output"] == {"temperature_f": 72}


def test_oversized_request_body_rejected(client: TestClient) -> None:
    session = _create_session(client)

    # Exceeds the 2MB transport-level body size limit even though no single
    # field exceeds its own limit checked at the schema level.
    huge_metadata = {f"key_{i}": "x" * 100 for i in range(30_000)}

    response = client.post(
        f"/sessions/{session['id']}/messages",
        json={
            "role": "user",
            "content": "Hello",
            "message_metadata": {"note": "irrelevant, body itself is huge"},
            "_padding": huge_metadata,
        },
    )

    assert response.status_code in (413, 422)

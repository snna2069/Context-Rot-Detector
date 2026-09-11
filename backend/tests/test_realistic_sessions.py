"""Realistic ingestion scenarios.

These tests only prove that the ingestion API can faithfully store and
order the kinds of conversations that later phases will analyze. They do
not perform any contradiction/fact-extraction/hallucination analysis --
that is out of scope until the analysis phases.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_session(client: TestClient, name: str) -> dict:
    response = client.post("/sessions", json={"name": name})
    assert response.status_code == 201
    return response.json()


def _add_message(client: TestClient, session_id: str, role: str, content: str) -> dict:
    response = client.post(
        f"/sessions/{session_id}/messages",
        json={"role": role, "content": content},
    )
    assert response.status_code == 201
    return response.json()


def test_healthy_session(client: TestClient) -> None:
    """A short, well-behaved back-and-forth with no red flags."""
    session = _create_session(client, "Healthy planning session")

    _add_message(
        client, session["id"], "system", "You are a helpful planning assistant."
    )
    _add_message(client, session["id"], "user", "Help me plan a 3-day trip to Kyoto.")
    _add_message(
        client,
        session["id"],
        "assistant",
        "Day 1: Fushimi Inari and Gion. Day 2: Arashiyama bamboo grove. "
        "Day 3: Kinkaku-ji and Nijo Castle.",
    )
    _add_message(client, session["id"], "user", "Great, book Day 1 activities.")
    _add_message(
        client, session["id"], "assistant", "Day 1 activities are booked for you."
    )

    timeline = client.get(f"/sessions/{session['id']}/timeline").json()
    assert len(timeline["messages"]) == 5
    assert [m["sequence_number"] for m in timeline["messages"]] == [1, 2, 3, 4, 5]


def test_long_session(client: TestClient) -> None:
    """A long session (50+ turns) to prove ordering holds at scale."""
    session = _create_session(client, "Long refactor pairing session")

    turn_count = 60
    for i in range(turn_count):
        role = "user" if i % 2 == 0 else "assistant"
        _add_message(
            client,
            session["id"],
            role,
            f"Turn {i}: continuing the refactor discussion.",
        )

    messages = client.get(f"/sessions/{session['id']}/messages").json()
    assert len(messages) == turn_count
    assert [m["sequence_number"] for m in messages] == list(range(1, turn_count + 1))


def test_contradictory_session(client: TestClient) -> None:
    """The assistant states two conflicting facts; ingestion just stores both.

    Detecting the contradiction is future analysis-layer work -- this test
    only proves both statements are captured faithfully in order.
    """
    session = _create_session(client, "Contradictory facts session")

    _add_message(client, session["id"], "user", "What is our project deadline?")
    first_claim = _add_message(
        client, session["id"], "assistant", "The project deadline is March 15th."
    )
    _add_message(client, session["id"], "user", "Are you sure? Double check.")
    second_claim = _add_message(
        client,
        session["id"],
        "assistant",
        "Actually, the project deadline is April 1st.",
    )

    assert "March 15th" in first_claim["content"]
    assert "April 1st" in second_claim["content"]

    messages = client.get(f"/sessions/{session['id']}/messages").json()
    assert len(messages) == 4


def test_session_with_tool_results(client: TestClient) -> None:
    """A session where the assistant calls a tool and uses its result."""
    session = _create_session(client, "Tool usage session")

    _add_message(client, session["id"], "user", "What's the weather in Tokyo?")
    assistant_message = _add_message(
        client, session["id"], "assistant", "Let me look that up."
    )

    tool_call = client.post(
        f"/sessions/{session['id']}/messages/{assistant_message['id']}/tool-calls",
        json={"tool_name": "get_weather", "arguments": {"city": "Tokyo"}},
    )
    assert tool_call.status_code == 201
    tool_call_body = tool_call.json()

    tool_result = client.post(
        f"/sessions/{session['id']}/tool-calls/{tool_call_body['id']}/result",
        json={"output": {"temperature_c": 18, "conditions": "cloudy"}},
    )
    assert tool_result.status_code == 201

    _add_message(
        client,
        session["id"],
        "assistant",
        "It's 18°C and cloudy in Tokyo right now.",
    )

    timeline = client.get(f"/sessions/{session['id']}/timeline").json()
    assistant_entry = timeline["messages"][1]
    assert len(assistant_entry["tool_calls"]) == 1
    assert assistant_entry["tool_calls"][0]["result"]["output"] == {
        "temperature_c": 18,
        "conditions": "cloudy",
    }


def test_session_with_ignored_information(client: TestClient) -> None:
    """The user states an important constraint that a later reply ignores.

    Ingestion only needs to store this faithfully; detecting that the
    constraint was ignored is future analysis-layer work.
    """
    session = _create_session(client, "Ignored constraint session")

    _add_message(
        client,
        session["id"],
        "user",
        "Important: I am allergic to shellfish, never suggest it.",
    )
    _add_message(
        client, session["id"], "assistant", "Understood, I will avoid shellfish."
    )
    _add_message(client, session["id"], "user", "Suggest a seafood restaurant menu.")
    ignoring_reply = _add_message(
        client,
        session["id"],
        "assistant",
        "How about a shrimp cocktail starter followed by grilled lobster?",
    )

    assert "shrimp" in ignoring_reply["content"].lower()

    messages = client.get(f"/sessions/{session['id']}/messages").json()
    assert len(messages) == 4
    assert messages[0]["content"].startswith("Important:")

from __future__ import annotations

from app.analysis.detectors.repetition import RepetitionDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message


def test_repetition_detects_near_duplicate_assistant_messages() -> None:
    messages = [
        make_message(1, MessageRole.USER, "What is the weather in Tokyo today?"),
        make_message(
            2,
            MessageRole.ASSISTANT,
            "The weather in Tokyo today is sunny with a high of 24 degrees.",
        ),
        make_message(3, MessageRole.USER, "And tomorrow?"),
        make_message(
            4,
            MessageRole.ASSISTANT,
            "The weather in Tokyo today is sunny with a high of 24 degrees.",
        ),
    ]
    context = make_context(messages)

    signals = RepetitionDetector().detect(context)

    assert len(signals) == 1
    assert signals[0].confidence >= 0.85
    assert set(signals[0].related_message_ids) == {messages[1].id, messages[3].id}


def test_repetition_no_signal_for_distinct_messages() -> None:
    messages = [
        make_message(1, MessageRole.USER, "What is the weather in Tokyo today?"),
        make_message(
            2, MessageRole.ASSISTANT, "It's sunny in Tokyo with a high of 24C."
        ),
        make_message(3, MessageRole.USER, "What about Osaka?"),
        make_message(
            4, MessageRole.ASSISTANT, "Osaka is expecting light rain this afternoon."
        ),
    ]
    context = make_context(messages)

    signals = RepetitionDetector().detect(context)

    assert signals == []


def test_repetition_ignores_short_generic_messages() -> None:
    messages = [
        make_message(1, MessageRole.ASSISTANT, "Okay."),
        make_message(2, MessageRole.ASSISTANT, "Okay."),
    ]
    context = make_context(messages)

    signals = RepetitionDetector().detect(context)

    assert signals == []

from __future__ import annotations

from app.analysis.detectors.stale_context import StaleContextDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message


def test_stale_context_flags_fact_not_reaffirmed() -> None:
    messages = [make_message(1, MessageRole.ASSISTANT, "The deadline is March 15th.")]
    messages += [
        make_message(i, MessageRole.ASSISTANT, f"Working on task number {i}.")
        for i in range(2, 13)
    ]
    context = make_context(messages)

    signals = StaleContextDetector().detect(context)

    assert len(signals) == 1
    assert signals[0].metadata["subject"] == "deadline"
    assert signals[0].confidence > 0


def test_stale_context_no_signal_when_recently_reaffirmed() -> None:
    messages = [
        make_message(1, MessageRole.ASSISTANT, "The deadline is March 15th."),
    ]
    messages += [
        make_message(i, MessageRole.ASSISTANT, f"Working on task number {i}.")
        for i in range(2, 12)
    ]
    messages.append(
        make_message(12, MessageRole.ASSISTANT, "The deadline is March 15th.")
    )
    context = make_context(messages)

    signals = StaleContextDetector().detect(context)

    assert signals == []


def test_stale_context_no_signal_for_short_session() -> None:
    messages = [
        make_message(1, MessageRole.ASSISTANT, "The deadline is March 15th."),
        make_message(2, MessageRole.ASSISTANT, "Sounds good."),
    ]
    context = make_context(messages)

    signals = StaleContextDetector().detect(context)

    assert signals == []
